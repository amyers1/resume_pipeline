"""
Improved Resume Pipeline API with production-ready features.

This version includes:
- Comprehensive input validation
- Structured error handling
- Response models for all endpoints
- Pagination for job listings
- CORS configuration
- Health check endpoints
- Improved SSE resource management
- Request ID tracking
"""

import asyncio
import json
import logging
import queue
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pika
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sse_starlette.sse import EventSourceResponse
from starlette.middleware.base import BaseHTTPMiddleware

from resume_pipeline_rabbitmq import RabbitMQConfig, publish_job_request

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# MIDDLEWARE
# ============================================================================


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracking."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
            },
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


# ============================================================================
# ERROR HANDLING
# ============================================================================

from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    JOB_NOT_FOUND = "job_not_found"
    VALIDATION_ERROR = "validation_error"
    FILE_NOT_FOUND = "file_not_found"
    INVALID_PATH = "invalid_path"
    QUEUE_ERROR = "queue_error"
    INTERNAL_ERROR = "internal_error"


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error_code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None


class ValidationError(Exception):
    """Custom validation error."""

    pass


class QueueConnectionError(Exception):
    """RabbitMQ connection error."""

    pass


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class JobBoardListContext(BaseModel):
    """Job board listing context."""

    search_keywords: Optional[str] = None
    search_location: Optional[str] = None
    search_radius_miles: Optional[int] = None
    employer_group_page: Optional[str] = None


class JobDetails(BaseModel):
    """Job details from posting."""

    source: Optional[str] = None
    platform: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    company_rating: Optional[str] = None
    location: Optional[str] = None
    location_detail: Optional[str] = None
    employment_type: Optional[str] = None
    pay_currency: Optional[str] = None
    pay_min_annual: Optional[int] = None
    pay_max_annual: Optional[int] = None
    pay_rate_type: Optional[str] = None
    pay_display: Optional[str] = None
    remote_type: Optional[str] = None
    job_post_url: Optional[str] = None
    apply_url: Optional[str] = None
    security_clearance_required: Optional[str] = None
    security_clearance_preferred: Optional[str] = None
    work_model: Optional[str] = None
    work_model_notes: Optional[str] = None
    posting_age: Optional[str] = None
    job_board_list_context: Optional[JobBoardListContext] = None


class Benefits(BaseModel):
    """Job benefits information."""

    listed_benefits: Optional[List[str]] = None
    benefits_text: Optional[str] = None
    eligibility_notes: Optional[str] = None
    relocation: Optional[str] = None
    sign_on_bonus: Optional[str] = None


class JobDescription(BaseModel):
    """Job description content."""

    headline: Optional[str] = None
    short_summary: Optional[str] = None
    full_text: Optional[str] = None
    required_experience_years_min: Optional[int] = None
    required_education: Optional[str] = None
    must_have_skills: Optional[List[str]] = None
    nice_to_have_skills: Optional[List[str]] = None


class JobData(BaseModel):
    """Complete job data."""

    job_details: JobDetails
    benefits: Benefits
    job_description: JobDescription

    @validator("job_details")
    def validate_job_details(cls, v):
        """Ensure critical job details are present."""
        if not v.company:
            raise ValueError("Company name is required")
        if not v.job_title:
            raise ValueError("Job title is required")
        return v


class ApiJobRequest(BaseModel):
    """Request model for new job submission."""

    job_data: JobData
    career_profile_path: str = "career_profile.json"
    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = Field(0, ge=0, le=10, description="Job priority (0-10)")
    enable_uploads: bool = True
    metadata: Optional[Dict[str, Any]] = None

    @validator("template")
    def validate_template(cls, v, values):
        """Validate template choice."""
        valid_templates = ["modern-deedy", "awesome-cv"]
        if v not in valid_templates:
            raise ValueError(f"Template must be one of: {', '.join(valid_templates)}")
        return v

    @validator("output_backend")
    def validate_backend(cls, v):
        """Validate output backend choice."""
        valid_backends = ["weasyprint", "latex"]
        if v not in valid_backends:
            raise ValueError(f"Backend must be one of: {', '.join(valid_backends)}")
        return v

    @validator("career_profile_path")
    def validate_career_profile_path(cls, v):
        """Validate career profile exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Career profile not found: {v}")
        if not path.is_file():
            raise ValueError(f"Career profile path is not a file: {v}")
        # Basic sanitization - prevent directory traversal
        if ".." in str(path) or str(path).startswith("/"):
            raise ValueError("Invalid career profile path")
        return v


class ResubmitJobRequest(BaseModel):
    """Request model for resubmitting existing job."""

    career_profile_path: str = "career_profile.json"
    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = Field(0, ge=0, le=10)
    enable_uploads: bool = True
    metadata: Optional[Dict[str, Any]] = None

    @validator("career_profile_path")
    def validate_career_profile_path(cls, v):
        """Validate career profile exists."""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Career profile not found: {v}")
        return v


class JobSubmissionResponse(BaseModel):
    """Response model for job submission."""

    message: str
    job_id: str
    job_json_path: str
    status_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JobListItem(BaseModel):
    """Single job in list response."""

    job_id: str
    company: str
    job_title: str
    created_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None


class PaginatedJobListResponse(BaseModel):
    """Paginated job list response."""

    jobs: List[JobListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Dict[str, bool]
    version: str


# ============================================================================
# SSE CONNECTION MANAGER
# ============================================================================


class SSEConnectionManager:
    """Manages SSE connections with proper resource cleanup."""

    def __init__(self):
        self.active_connections: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()

    def create_connection(self, connection_id: str) -> queue.Queue:
        """Create a new SSE connection."""
        q = queue.Queue(maxsize=100)  # Prevent unbounded memory growth

        with self._lock:
            self.active_connections[connection_id] = q

        logger.info(f"SSE connection created: {connection_id}")
        return q

    def remove_connection(self, connection_id: str):
        """Remove an SSE connection."""
        with self._lock:
            if connection_id in self.active_connections:
                self.active_connections.pop(connection_id)
                logger.info(f"SSE connection removed: {connection_id}")


# Global SSE manager
sse_manager = SSEConnectionManager()


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================


def validate_job_id(job_id: str) -> None:
    """
    Validate job ID format.

    Args:
        job_id: Job identifier to validate

    Raises:
        ValidationError: If job ID is invalid
    """
    # Check for directory traversal attempts
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        raise ValidationError("Invalid job ID: contains illegal characters")

    # Check length
    if len(job_id) > 200:
        raise ValidationError("Invalid job ID: too long")


def validate_job_submission(request: ApiJobRequest) -> None:
    """
    Validate job submission inputs beyond Pydantic validation.

    Args:
        request: Job submission request

    Raises:
        ValidationError: If validation fails
    """
    # Career profile path already validated by Pydantic

    # Validate template/backend combination
    if request.output_backend == "latex":
        valid_latex_templates = ["modern-deedy", "awesome-cv"]
        if request.template not in valid_latex_templates:
            raise ValidationError(
                f"Invalid LaTeX template: {request.template}. "
                f"Must be one of: {', '.join(valid_latex_templates)}"
            )

    # Validate job data has meaningful content
    if request.job_data.job_description.full_text:
        text_length = len(request.job_data.job_description.full_text.strip())
        if text_length < 50:
            raise ValidationError(
                "Job description text is too short (minimum 50 characters)"
            )


# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(
    title="Resume Pipeline API",
    description="Production-ready API for submitting resume generation jobs",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware
app.add_middleware(RequestIDMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev
        "http://localhost:8080",  # Vue dev
        "http://localhost:5173",  # Vite dev
        # Add production origins as needed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation errors consistently."""
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=str(exc),
            request_id=request.state.request_id
            if hasattr(request.state, "request_id")
            else None,
        ).dict(),
    )


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle file not found errors."""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error_code=ErrorCode.FILE_NOT_FOUND,
            message=str(exc),
            request_id=request.state.request_id
            if hasattr(request.state, "request_id")
            else None,
        ).dict(),
    )


@app.exception_handler(QueueConnectionError)
async def queue_error_handler(request: Request, exc: QueueConnectionError):
    """Handle RabbitMQ connection errors."""
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error_code=ErrorCode.QUEUE_ERROR,
            message="Job queue service unavailable",
            details={"error": str(exc)},
            request_id=request.state.request_id
            if hasattr(request.state, "request_id")
            else None,
        ).dict(),
    )


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Resume Pipeline API is running",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    description="Check the health status of the API and its dependencies",
)
def health_check():
    """
    Comprehensive health check.

    Checks:
    - RabbitMQ connection
    - Jobs directory access
    - File system write permissions
    """
    checks = {}

    # Check RabbitMQ connection
    try:
        config = RabbitMQConfig()
        connection = pika.BlockingConnection(config.get_connection_params())
        connection.close()
        checks["rabbitmq"] = True
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}")
        checks["rabbitmq"] = False

    # Check jobs directory
    jobs_dir = Path("jobs")
    checks["jobs_directory"] = jobs_dir.exists() and jobs_dir.is_dir()

    # Check write permissions
    try:
        test_file = jobs_dir / ".health_check"
        test_file.touch()
        test_file.unlink()
        checks["file_system_writable"] = True
    except Exception:
        checks["file_system_writable"] = False

    # Determine overall status
    all_healthy = all(checks.values())
    some_healthy = any(checks.values())

    if all_healthy:
        status = HealthStatus.HEALTHY
    elif some_healthy:
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.UNHEALTHY

    return HealthCheckResponse(status=status, checks=checks, version="1.0.0")


@app.get("/ready")
def readiness_check():
    """
    Simple readiness check for orchestration systems.

    Returns 200 if ready, 503 if not ready.
    """
    health = health_check()
    if health.status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"ready": True}


@app.get(
    "/jobs",
    response_model=PaginatedJobListResponse,
    summary="List jobs with pagination",
    description="Get a paginated list of all jobs with optional filtering",
)
def list_jobs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    company: Optional[str] = Query(None, description="Filter by company name"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
):
    """
    List all available jobs with pagination.

    This endpoint scans the 'jobs' directory and returns a summary of each
    job JSON file found.

    Query Parameters:
    - page: Page number (1-indexed)
    - page_size: Number of items per page (1-100)
    - company: Filter by company name (optional)
    - sort_by: Field to sort by (default: created_at)
    - sort_order: Sort order: asc or desc (default: desc)
    """
    jobs_dir = Path("jobs")
    if not jobs_dir.exists():
        return PaginatedJobListResponse(
            jobs=[], total_count=0, page=page, page_size=page_size, total_pages=0
        )

    # Collect all jobs
    all_jobs = []
    for job_file in jobs_dir.glob("*.json"):
        if job_file.name == "schema.json":
            continue

        try:
            # Get file metadata
            file_stat = job_file.stat()
            created_at = datetime.fromtimestamp(file_stat.st_ctime)

            with open(job_file, "r") as f:
                job_data = json.load(f)
                job_details = job_data.get("job_details", {})

                # Apply company filter
                job_company = job_details.get("company", "Unknown")
                if company and job_company.lower() != company.lower():
                    continue

                all_jobs.append(
                    JobListItem(
                        job_id=job_file.stem,
                        company=job_company,
                        job_title=job_details.get("job_title", "Unknown"),
                        created_at=created_at,
                        file_size_bytes=file_stat.st_size,
                    )
                )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not parse {job_file.name}: {e}")
            # Include in list with error indicator
            all_jobs.append(
                JobListItem(
                    job_id=job_file.stem,
                    company="Invalid Format",
                    job_title="Invalid Format",
                )
            )

    # Sort jobs
    reverse = sort_order == "desc"
    if sort_by == "created_at" and all_jobs:
        # Sort by created_at, handling None values
        all_jobs.sort(
            key=lambda x: x.created_at if x.created_at else datetime.min,
            reverse=reverse,
        )
    elif sort_by == "company":
        all_jobs.sort(key=lambda x: x.company.lower(), reverse=reverse)
    elif sort_by == "job_title":
        all_jobs.sort(key=lambda x: x.job_title.lower(), reverse=reverse)

    # Pagination
    total_count = len(all_jobs)
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    # Validate page number
    if page > total_pages and total_pages > 0:
        raise HTTPException(
            status_code=400, detail=f"Page {page} exceeds total pages ({total_pages})"
        )

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_jobs = all_jobs[start_idx:end_idx]

    return PaginatedJobListResponse(
        jobs=paginated_jobs,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.post(
    "/jobs",
    status_code=201,
    response_model=JobSubmissionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        503: {"model": ErrorResponse, "description": "Queue service unavailable"},
    },
    summary="Submit a new job",
    description="Submit a new resume generation job to the pipeline",
)
def submit_job(request: ApiJobRequest, http_request: Request):
    """
    Submit a new resume generation job.

    This endpoint accepts job details in JSON format, validates the input,
    saves it to a file, and publishes a job request to the RabbitMQ queue.

    The job will be processed asynchronously by a worker. Use the returned
    status_url to monitor progress via Server-Sent Events.
    """
    job_id = f"api-job-{uuid.uuid4()}"
    request_id = (
        http_request.state.request_id
        if hasattr(http_request.state, "request_id")
        else "unknown"
    )

    logger.info(
        f"Job submission received",
        extra={
            "job_id": job_id,
            "request_id": request_id,
            "company": request.job_data.job_details.company,
            "job_title": request.job_data.job_details.job_title,
        },
    )

    # Validate request
    try:
        validate_job_submission(request)
    except ValidationError as e:
        logger.error(f"Validation failed for job {job_id}: {e}")
        raise

    # Define path for the new job JSON file
    jobs_dir = Path("jobs")
    jobs_dir.mkdir(exist_ok=True)
    job_json_path = jobs_dir / f"{job_id}.json"

    try:
        # Save the job data to a file
        with open(job_json_path, "w") as f:
            json.dump(request.job_data.dict(), f, indent=2)
        logger.info(f"Saved job data to {job_json_path}")

        # Publish the job to the queue
        try:
            published_job_id = publish_job_request(
                job_json_path=str(job_json_path),
                career_profile_path=request.career_profile_path,
                template=request.template,
                output_backend=request.output_backend,
                priority=request.priority,
                enable_uploads=request.enable_uploads,
                metadata=request.metadata,
            )
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection failed for job {job_id}: {e}")
            # Clean up created job file
            if job_json_path.exists():
                job_json_path.unlink()
            raise QueueConnectionError(f"Failed to connect to job queue: {e}")

        logger.info(
            f"Successfully published job to RabbitMQ",
            extra={"job_id": published_job_id, "request_id": request_id},
        )

        return JobSubmissionResponse(
            message="Job submitted successfully",
            job_id=published_job_id,
            job_json_path=str(job_json_path),
            status_url=f"/jobs/{published_job_id}/status",
        )

    except Exception as e:
        logger.error(
            f"Failed to submit job {job_id}: {e}", extra={"request_id": request_id}
        )
        # Clean up created job file if something goes wrong
        if job_json_path.exists():
            job_json_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Internal server error",
                details={"error": str(e)},
                request_id=request_id,
            ).dict(),
        )


@app.post(
    "/jobs/{job_id}/submit",
    status_code=202,
    response_model=JobSubmissionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        503: {"model": ErrorResponse, "description": "Queue service unavailable"},
    },
    summary="Resubmit an existing job",
    description="Resubmit an existing job with optional parameter changes",
)
def resubmit_job(job_id: str, request: ResubmitJobRequest, http_request: Request):
    """
    Resubmit an existing job.

    This endpoint finds a job by its ID and submits it to the pipeline again
    with the provided options. This is useful for:
    - Regenerating a resume with a different template
    - Retrying a failed job
    - Creating a new version with updated settings
    """
    request_id = (
        http_request.state.request_id
        if hasattr(http_request.state, "request_id")
        else "unknown"
    )

    # Validate job_id format
    try:
        validate_job_id(job_id)
    except ValidationError as e:
        logger.error(f"Invalid job ID: {job_id}")
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(
        f"Resubmit request received", extra={"job_id": job_id, "request_id": request_id}
    )

    # Find the job JSON file
    job_json_path = Path("jobs") / f"{job_id}.json"
    if not job_json_path.exists():
        logger.warning(f"Job not found: {job_id}")
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error_code=ErrorCode.JOB_NOT_FOUND,
                message=f"Job '{job_id}' not found",
                request_id=request_id,
            ).dict(),
        )

    try:
        # Publish the job to the queue
        published_job_id = publish_job_request(
            job_json_path=str(job_json_path),
            career_profile_path=request.career_profile_path,
            template=request.template,
            output_backend=request.output_backend,
            priority=request.priority,
            enable_uploads=request.enable_uploads,
            metadata=request.metadata,
        )

        logger.info(
            f"Successfully resubmitted job",
            extra={
                "original_job_id": job_id,
                "new_job_id": published_job_id,
                "request_id": request_id,
            },
        )

        return JobSubmissionResponse(
            message="Job resubmitted successfully",
            job_id=published_job_id,
            job_json_path=str(job_json_path),
            status_url=f"/jobs/{published_job_id}/status",
        )

    except pika.exceptions.AMQPConnectionError as e:
        logger.error(f"RabbitMQ connection failed for resubmit {job_id}: {e}")
        raise QueueConnectionError(f"Failed to connect to job queue: {e}")

    except Exception as e:
        logger.error(
            f"Failed to resubmit job {job_id}: {e}", extra={"request_id": request_id}
        )
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Internal server error",
                details={"error": str(e)},
                request_id=request_id,
            ).dict(),
        )


# ============================================================================
# SSE STATUS ENDPOINTS
# ============================================================================


async def status_event_generator(job_id: Optional[str] = None):
    """
    Improved SSE generator with proper resource management.

    Args:
        job_id: Optional job ID to filter events for

    Yields:
        Server-Sent Events with job status updates
    """
    connection_id = str(uuid.uuid4())
    connection: Optional[pika.BlockingConnection] = None
    channel: Optional[pika.channel.Channel] = None

    # Create connection queue
    q = sse_manager.create_connection(connection_id)

    def consumer_callback(ch, method, properties, body):
        """Callback to put messages in the queue."""
        try:
            q.put_nowait(body)
        except queue.Full:
            logger.warning(
                f"SSE queue full for connection {connection_id}, dropping message"
            )

        # Check if we should stop consuming for single job monitoring
        if job_id:
            try:
                status = json.loads(body)
                if status.get("job_id") == job_id and status.get("status") in [
                    "job_completed",
                    "job_failed",
                ]:
                    ch.stop_consuming()
            except (json.JSONDecodeError, KeyError):
                pass

    def start_consumer():
        """Connects to RabbitMQ and starts consuming messages."""
        nonlocal connection, channel
        config = RabbitMQConfig()

        try:
            connection = pika.BlockingConnection(config.get_connection_params())
            channel = connection.channel()

            # Consume from both status and progress queues
            for queue_name in [config.status_queue, config.progress_queue]:
                channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=consumer_callback,
                    auto_ack=True,
                )

            logger.info(
                f"SSE consumer started",
                extra={"connection_id": connection_id, "job_id": job_id or "all"},
            )
            channel.start_consuming()

        except Exception as e:
            logger.error(f"SSE consumer error for {connection_id}: {e}")
            try:
                error_msg = json.dumps({"error": str(e)})
                q.put_nowait(error_msg.encode())
            except queue.Full:
                pass
        finally:
            # Clean shutdown
            if channel and channel.is_open:
                try:
                    channel.stop_consuming()
                    channel.close()
                except Exception as e:
                    logger.error(f"Error closing channel for {connection_id}: {e}")

            if connection and connection.is_open:
                try:
                    connection.close()
                except Exception as e:
                    logger.error(f"Error closing connection for {connection_id}: {e}")

            # Signal completion
            try:
                q.put_nowait(None)
            except queue.Full:
                pass

    # Start consumer thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    # Connection timeout
    timeout_seconds = 300  # 5 minutes
    start_time = datetime.utcnow()

    try:
        while True:
            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                logger.warning(
                    f"SSE connection timeout",
                    extra={
                        "connection_id": connection_id,
                        "job_id": job_id or "all",
                        "elapsed_seconds": elapsed,
                    },
                )
                break

            # Get message with timeout
            try:
                message_body = await asyncio.to_thread(q.get, timeout=1)
            except queue.Empty:
                # Send keep-alive ping
                yield {
                    "event": "ping",
                    "data": json.dumps({"timestamp": datetime.utcnow().isoformat()}),
                }
                continue

            # Check for termination signal
            if message_body is None:
                logger.info(f"SSE consumer stopped for {connection_id}")
                break

            # Parse and filter message
            try:
                status = json.loads(message_body)

                # Filter by job_id if specified
                if job_id and status.get("job_id") != job_id:
                    continue

                yield {"event": "message", "data": json.dumps(status)}

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse SSE message: {e}")
                continue

    except asyncio.CancelledError:
        logger.info(f"SSE client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"SSE generator error for {connection_id}: {e}")
    finally:
        # Cleanup
        sse_manager.remove_connection(connection_id)

        # Ensure consumer thread stops
        if consumer_thread.is_alive() and channel:
            try:
                channel.stop_consuming()
            except:
                pass

        logger.info(f"SSE generator finished for {connection_id}")


@app.get(
    "/jobs/status",
    summary="Stream all job status updates",
    description="Server-Sent Events endpoint for monitoring all job status updates in real-time",
)
async def stream_all_jobs_status():
    """
    Stream status updates for all jobs using Server-Sent Events.

    This endpoint provides real-time updates for all jobs in the system.
    Connect to this endpoint with an EventSource client to receive updates.

    Example JavaScript client:
    ```javascript
    const eventSource = new EventSource('/jobs/status');
    eventSource.onmessage = (event) => {
        const status = JSON.parse(event.data);
        console.log('Job update:', status);
    };
    ```
    """
    return EventSourceResponse(status_event_generator())


@app.get(
    "/jobs/{job_id}/status",
    summary="Stream specific job status updates",
    description="Server-Sent Events endpoint for monitoring a specific job's status in real-time",
)
async def stream_job_status(job_id: str):
    """
    Stream status updates for a specific job using Server-Sent Events.

    This endpoint provides real-time updates for a single job. The connection
    will automatically close when the job reaches a terminal state (completed or failed).

    Example JavaScript client:
    ```javascript
    const eventSource = new EventSource('/jobs/your-job-id/status');
    eventSource.onmessage = (event) => {
        const status = JSON.parse(event.data);
        console.log('Job status:', status);

        if (status.status === 'job_completed' || status.status === 'job_failed') {
            eventSource.close();
        }
    };
    ```
    """
    # Validate job_id
    try:
        validate_job_id(job_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return EventSourceResponse(status_event_generator(job_id=job_id))


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Resume Pipeline API starting up")

    # Ensure jobs directory exists
    jobs_dir = Path("jobs")
    jobs_dir.mkdir(exist_ok=True)

    # Log configuration
    logger.info(f"Jobs directory: {jobs_dir.absolute()}")

    # Test RabbitMQ connection
    try:
        config = RabbitMQConfig()
        connection = pika.BlockingConnection(config.get_connection_params())
        connection.close()
        logger.info("RabbitMQ connection test successful")
    except Exception as e:
        logger.warning(f"RabbitMQ connection test failed: {e}")
        logger.warning("API will continue but job submission may fail")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Resume Pipeline API shutting down")

    # Close any remaining SSE connections
    active_count = len(sse_manager.active_connections)
    if active_count > 0:
        logger.info(f"Closing {active_count} active SSE connections")


# ============================================================================
# MAIN - For development only
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_improved:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
