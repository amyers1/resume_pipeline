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
- Job metadata tracking (P0)
- File download endpoints (P0)
- Job details endpoint (P0)
- Profile management (P1)
- Job deletion (P2)
- List job files (P2)
"""

import asyncio
import json
import logging
import os
import queue
import re
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pika
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from sse_starlette.sse import EventSourceResponse
from starlette.middleware.base import BaseHTTPMiddleware

from resume_pipeline_rabbitmq import RabbitMQConfig, publish_job_request

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
JOBS_DIR = Path("jobs")
OUTPUT_DIR = Path("output")
PROFILES_DIR = Path("profiles")

# Ensure directories exist
JOBS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
PROFILES_DIR.mkdir(exist_ok=True)


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
    CONFLICT = "conflict"


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


class JobSubmitRequest(BaseModel):
    job_data: Optional[JobData] = None
    job_template_path: Optional[str] = None
    career_profile_path: str
    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = 5
    enable_uploads: bool = True


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
    status: Optional[str] = None
    file_size_bytes: Optional[int] = None


class PaginatedJobListResponse(BaseModel):
    """Paginated job list response."""

    jobs: List[JobListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class JobDetailsResponse(BaseModel):
    """Complete job details response."""

    job_id: str
    company: str
    job_title: str
    created_at: str
    status: str
    template: str
    output_backend: str
    priority: int
    job_description: Optional[str] = None
    output_dir: Optional[str] = None
    output_files: Optional[Dict[str, str]] = None
    completed_at: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    final_score: Optional[float] = None
    error: Optional[str] = None


class FileInfo(BaseModel):
    """File metadata."""

    name: str
    type: str
    size_bytes: int
    created_at: str
    download_url: str


class ProfileInfo(BaseModel):
    """Career profile information."""

    filename: str
    size_bytes: int
    uploaded_at: str


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
# METADATA MANAGEMENT
# ============================================================================


def create_job_metadata(job_id: str, job_data: dict) -> dict:
    """Create initial job metadata file"""
    metadata = {
        "job_id": job_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "company": job_data.get("job_details", {}).get("company", ""),
        "job_title": job_data.get("job_details", {}).get("job_title", ""),
        "template": "awesome-cv",  # Will be updated by worker
        "output_backend": "weasyprint",  # Will be updated by worker
        "priority": 5,  # Will be updated by worker
        "status": "queued",
        "output_dir": None,
        "completed_at": None,
        "processing_time_seconds": None,
        "final_score": None,
        "error": None,
    }

    metadata_path = JOBS_DIR / f"{job_id}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Created metadata for job {job_id}")
    return metadata


def update_job_metadata(job_id: str, updates: dict) -> Optional[dict]:
    """Update job metadata file"""
    metadata_path = JOBS_DIR / f"{job_id}_metadata.json"

    if not metadata_path.exists():
        logger.warning(f"Metadata file not found for job {job_id}")
        return None

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        metadata.update(updates)

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Updated metadata for job {job_id}: {updates}")
        return metadata
    except Exception as e:
        logger.error(f"Failed to update metadata for job {job_id}: {e}")
        return None


def get_job_metadata(job_id: str) -> Optional[dict]:
    """Retrieve job metadata"""
    metadata_path = JOBS_DIR / f"{job_id}_metadata.json"

    if not metadata_path.exists():
        return None

    try:
        with open(metadata_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read metadata for job {job_id}: {e}")
        return None


def validate_job_id_format(job_id: str) -> bool:
    """Validate job ID format"""
    # Check for directory traversal attempts
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        return False
    # Check length
    if len(job_id) > 200:
        return False
    return True


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    # Remove any path components
    filename = os.path.basename(filename)
    # Remove any non-alphanumeric characters except dots, dashes, underscores
    filename = re.sub(r"[^\w\-.]", "_", filename)
    return filename


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
    if not validate_job_id_format(job_id):
        raise ValidationError("Invalid job ID format")


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
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware
app.add_middleware(RequestIDMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        # "http://localhost:3000",  # React dev
        # "http://localhost:8080",  # Vue dev
        # "http://localhost:5173",  # Vite dev
        # "http://0.0.0.0:3000",  # React dev
        # "http://0.0.0.0:8080",  # Vue dev
        # "http://0.0.0.0:5173",  # Vite dev
        # # Add production origins as needed
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
        "version": "2.0.0",
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
    checks["jobs_directory"] = JOBS_DIR.exists() and JOBS_DIR.is_dir()

    # Check write permissions
    try:
        test_file = JOBS_DIR / ".health_check"
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

    return HealthCheckResponse(status=status, checks=checks, version="2.0.0")


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


@app.get("/job-templates")
def list_job_templates():
    """List available job template files."""
    jobs_dir = Path("jobs")
    templates = []

    if jobs_dir.exists():
        templates = [
            f.name
            for f in jobs_dir.glob("*.json")
            if not f.name.startswith(".") and not f.name.endswith("_metadata.json")
        ]
        templates.sort()

    return {"templates": templates}


@app.get("/job-templates/{filename}")
def get_job_template(filename: str):
    """Get the content of a specific job template."""
    # Validate filename
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")

    template_path = JOBS_DIR / filename

    if not template_path.exists():
        raise HTTPException(404, f"Template '{filename}' not found")

    try:
        with open(template_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Failed to read template: {e}")


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
    job JSON file found, including metadata status if available.
    """
    if not JOBS_DIR.exists():
        return PaginatedJobListResponse(
            jobs=[], total_count=0, page=page, page_size=page_size, total_pages=0
        )

    # Collect all jobs
    all_jobs = []
    for file in JOBS_DIR.glob("*_metadata.json"):
        job_id = file.stem.replace("_metadata", "")
        with open(file, "r") as f:
            metadata = json.load(f)

            # Apply company filter
            if company and metadata.get("company", "").lower() != company.lower():
                continue

            all_jobs.append(
                JobListItem(
                    job_id=job_id,
                    company=metadata.get("company", "Unknown"),
                    job_title=metadata.get("job_title", "Unknown"),
                    created_at=metadata.get("created_at"),
                    status=metadata.get("status", "unknown"),
                    file_size_bytes=file.stat().st_size,
                )
            )

    # Sort jobs
    reverse = sort_order == "desc"
    if sort_by == "created_at" and all_jobs:
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


@app.get(
    "/jobs/{job_id}",
    response_model=JobDetailsResponse,
    summary="Get complete job details",
    description="Retrieve complete information about a specific job including status and output files",
)
def get_job_details(job_id: str):
    """Get complete job details including metadata and output files."""
    try:
        validate_job_id(job_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_file = JOBS_DIR / f"{job_id}.json"
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    # Read job data
    with open(job_file, "r") as f:
        job_data = json.load(f)

    # Read metadata
    metadata = get_job_metadata(job_id)
    if not metadata:
        # If metadata doesn't exist, create basic response from job data
        return JobDetailsResponse(
            job_id=job_id,
            company=job_data.get("job_details", {}).get("company", "Unknown"),
            job_title=job_data.get("job_details", {}).get("job_title", "Unknown"),
            created_at=datetime.utcfromtimestamp(job_file.stat().st_mtime).isoformat()
            + "Z",
            status="unknown",
            template="awesome-cv",
            output_backend="weasyprint",
            priority=5,
            job_description=job_data.get("job_description", {}).get("full_text"),
        )

    # Get output files if available
    output_files = None
    if metadata.get("output_dir"):
        output_dir = Path(metadata["output_dir"])
        if output_dir.exists():
            output_files = {}
            for ext in [".pdf", ".tex", ".json"]:
                files = list(output_dir.glob(f"*{ext}"))
                if files:
                    output_files[ext[1:]] = str(files[0])

    return JobDetailsResponse(
        job_id=job_id,
        company=job_data.get("job_details", {}).get("company", "Unknown"),
        job_title=job_data.get("job_details", {}).get("job_title", "Unknown"),
        created_at=metadata.get("created_at"),
        status=metadata.get("status", "unknown"),
        template=metadata.get("template", "awesome-cv"),
        output_backend=metadata.get("output_backend", "weasyprint"),
        priority=metadata.get("priority", 5),
        job_description=job_data.get("job_description", {}).get("full_text"),
        output_dir=metadata.get("output_dir"),
        output_files=output_files,
        completed_at=metadata.get("completed_at"),
        processing_time_seconds=metadata.get("processing_time_seconds"),
        final_score=metadata.get("final_score"),
        error=metadata.get("error"),
    )


@app.get(
    "/jobs/{job_id}/files",
    summary="List all files for a job",
    description="Get a list of all output files available for a specific job",
)
def list_job_files(job_id: str):
    """List all output files for a job."""
    try:
        validate_job_id(job_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    metadata = get_job_metadata(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    output_dir = metadata.get("output_dir")
    if not output_dir or not Path(output_dir).exists():
        return {"job_id": job_id, "files": []}

    output_path = Path(output_dir)
    files = []

    for file_path in output_path.iterdir():
        if file_path.is_file():
            stat = file_path.stat()

            # Determine content type
            ext = file_path.suffix.lower()
            content_type = {
                ".pdf": "application/pdf",
                ".tex": "text/x-tex",
                ".json": "application/json",
                ".txt": "text/plain",
            }.get(ext, "application/octet-stream")

            files.append(
                FileInfo(
                    name=file_path.name,
                    type=content_type,
                    size_bytes=stat.st_size,
                    created_at=datetime.utcfromtimestamp(stat.st_mtime).isoformat()
                    + "Z",
                    download_url=f"/jobs/{job_id}/files/{file_path.name}",
                )
            )

    return {"job_id": job_id, "files": files}


@app.get(
    "/jobs/{job_id}/files/{filename}",
    summary="Download job output file",
    description="Download a specific output file from a completed job",
)
def download_job_file(job_id: str, filename: str):
    """Download a specific file from a job's output."""
    try:
        validate_job_id(job_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Sanitize filename to prevent path traversal
    filename = sanitize_filename(filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Get job metadata to find output directory
    metadata = get_job_metadata(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    output_dir = metadata.get("output_dir")
    if not output_dir:
        raise HTTPException(status_code=404, detail="Job output not available yet")

    file_path = Path(output_dir) / filename

    # Verify file exists and is within output directory
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Verify file is actually in the output directory (prevent traversal)
    try:
        file_path.resolve().relative_to(Path(output_dir).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    # Determine content type
    ext = file_path.suffix.lower()
    content_type = {
        ".pdf": "application/pdf",
        ".tex": "text/x-tex",
        ".json": "application/json",
        ".txt": "text/plain",
    }.get(ext, "application/octet-stream")

    return FileResponse(path=str(file_path), media_type=content_type, filename=filename)


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
def submit_job(request: JobSubmitRequest, http_request: Request):
    """
    Submit a new resume generation job.

    This endpoint accepts job details in JSON format, validates the input,
    saves it to a file, creates metadata, and publishes a job request to the queue.
    """
    # Validate that exactly one source is provided
    if not request.job_data and not request.job_template_path:
        raise HTTPException(
            400, "Either job_data or job_template_path must be provided"
        )

    if request.job_data and request.job_template_path:
        raise HTTPException(400, "Cannot provide both job_data and job_template_path")

    job_id = f"api-job-{uuid.uuid4()}"
    request_id = (
        http_request.state.request_id
        if hasattr(http_request.state, "request_id")
        else "unknown"
    )

    # Load job data from template if specified
    if request.job_template_path:
        template_path = JOBS_DIR / request.job_template_path
        if not template_path.exists():
            raise HTTPException(
                404, f"Template '{request.job_template_path}' not found"
            )

        with open(template_path, "r") as f:
            job_data = json.load(f)
    else:
        job_data = request.job_data.dict()

    logger.info(
        f"Job submission received",
        extra={
            "job_id": job_id,
            "request_id": request_id,
            "company": job_data.get("job_details", {}).get("company", ""),
            "job_title": job_data.get("job_details", {}).get("job_title", ""),
        },
    )

    # Validate request
    # try:
    #     validate_job_submission(request)
    # except ValidationError as e:
    #     logger.error(f"Validation failed for job {job_id}: {e}")
    #     raise

    # Define path for the new job JSON file
    job_json_path = JOBS_DIR / f"{job_id}.json"

    try:
        # Save the job data to a file
        with open(job_json_path, "w") as f:
            json.dump(job_data, f, indent=2)
        logger.info(f"Saved job data to {job_json_path}")

        # Create metadata
        create_job_metadata(job_id, job_data)

        # Publish the job to the queue
        try:
            published_job_id = publish_job_request(
                job_json_path=str(job_json_path),
                career_profile_path=request.career_profile_path,
                template=request.template,
                output_backend=request.output_backend,
                priority=request.priority,
                enable_uploads=request.enable_uploads,
                metadata=None,  # request.metadata,
                job_id=job_id,
            )
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection failed for job {job_id}: {e}")
            # Clean up created files
            if job_json_path.exists():
                job_json_path.unlink()
            metadata_path = JOBS_DIR / f"{job_id}_metadata.json"
            if metadata_path.exists():
                metadata_path.unlink()
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
        # Clean up created files
        if job_json_path.exists():
            job_json_path.unlink()
        metadata_path = JOBS_DIR / f"{job_id}_metadata.json"
        if metadata_path.exists():
            metadata_path.unlink()
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
    with the provided options.
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
    job_json_path = JOBS_DIR / f"{job_id}.json"
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

    # Update metadata status to queued
    update_job_metadata(
        job_id, {"status": "queued", "error": None, "completed_at": None}
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
            job_id=job_id,
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


@app.delete(
    "/jobs/{job_id}",
    summary="Delete a job",
    description="Delete a job and its metadata files",
)
def delete_job(job_id: str):
    """Delete a job and its metadata."""
    try:
        validate_job_id(job_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_file = JOBS_DIR / f"{job_id}.json"
    metadata_file = JOBS_DIR / f"{job_id}_metadata.json"

    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if job is currently processing
    metadata = get_job_metadata(job_id)
    if metadata and metadata.get("status") == "processing":
        raise HTTPException(
            status_code=409, detail="Cannot delete job while it is processing"
        )

    deleted_count = 0

    # Delete job file
    if job_file.exists():
        job_file.unlink()
        deleted_count += 1
        logger.info(f"Deleted job file: {job_file}")

    # Delete metadata file
    if metadata_file.exists():
        metadata_file.unlink()
        deleted_count += 1
        logger.info(f"Deleted metadata file: {metadata_file}")

    return {
        "message": "Job deleted successfully",
        "job_id": job_id,
        "files_deleted": deleted_count,
    }


# ============================================================================
# PROFILE ENDPOINTS
# ============================================================================


@app.post(
    "/profiles",
    summary="Upload career profile",
    description="Upload a career profile JSON file",
)
async def upload_profile(file: UploadFile = File(...)):
    """Upload a career profile JSON file."""
    # Validate file extension
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    # Read and validate JSON content
    try:
        content = await file.read()
        json.loads(content)  # Validate JSON
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON content")

    # Sanitize filename
    filename = sanitize_filename(file.filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Save file
    file_path = PROFILES_DIR / filename
    with open(file_path, "wb") as f:
        f.write(content)

    stat = file_path.stat()
    logger.info(f"Profile uploaded: {filename} ({stat.st_size} bytes)")

    return {
        "filename": filename,
        "size_bytes": stat.st_size,
        "uploaded_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z",
        "path": str(file_path),
    }


@app.get(
    "/profiles",
    summary="List career profiles",
    description="Get a list of all available career profiles",
)
def list_profiles():
    """List all available career profiles."""
    profiles = []

    for profile_file in PROFILES_DIR.glob("*.json"):
        try:
            stat = profile_file.stat()
            profiles.append(
                ProfileInfo(
                    filename=profile_file.name,
                    size_bytes=stat.st_size,
                    uploaded_at=datetime.utcfromtimestamp(stat.st_mtime).isoformat()
                    + "Z",
                )
            )
        except Exception as e:
            logger.error(f"Error reading profile {profile_file}: {e}")

    # Sort by upload date (newest first)
    profiles.sort(key=lambda x: x.uploaded_at, reverse=True)

    return {"profiles": profiles}


@app.delete(
    "/profiles/{filename}",
    summary="Delete career profile",
    description="Delete a career profile file",
)
def delete_profile(filename: str):
    """Delete a career profile."""
    # Sanitize filename to prevent path traversal
    filename = sanitize_filename(filename)
    if not filename or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = PROFILES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Profile not found")

    file_path.unlink()
    logger.info(f"Deleted profile: {filename}")

    return {"message": "Profile deleted successfully", "filename": filename}


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

    The connection will automatically close when the job reaches a terminal state.
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

    # Ensure directories exist
    JOBS_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    PROFILES_DIR.mkdir(exist_ok=True)

    # Log configuration
    logger.info(f"Jobs directory: {JOBS_DIR.absolute()}")
    logger.info(f"Output directory: {OUTPUT_DIR.absolute()}")
    logger.info(f"Profiles directory: {PROFILES_DIR.absolute()}")

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

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
