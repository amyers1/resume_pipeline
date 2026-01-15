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
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from resume_pipeline_rabbitmq import RabbitMQConfig, publish_job_request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Pydantic Models based on schema.json ---


class JobBoardListContext(BaseModel):
    search_keywords: Optional[str] = None
    search_location: Optional[str] = None
    search_radius_miles: Optional[int] = None
    employer_group_page: Optional[str] = None


class JobDetails(BaseModel):
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
    listed_benefits: Optional[List[str]] = None
    benefits_text: Optional[str] = None
    eligibility_notes: Optional[str] = None
    relocation: Optional[str] = None
    sign_on_bonus: Optional[str] = None


class JobDescription(BaseModel):
    headline: Optional[str] = None
    short_summary: Optional[str] = None
    full_text: Optional[str] = None
    required_experience_years_min: Optional[int] = None
    required_education: Optional[str] = None
    must_have_skills: Optional[List[str]] = None
    nice_to_have_skills: Optional[List[str]] = None


class JobData(BaseModel):
    job_details: JobDetails
    benefits: Benefits
    job_description: JobDescription


class ApiJobRequest(BaseModel):
    job_data: JobData
    career_profile_path: str = "career_profile.json"
    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = Field(0, ge=0, le=10)
    enable_uploads: bool = True
    metadata: Optional[Dict[str, Any]] = None


class ResubmitJobRequest(BaseModel):
    career_profile_path: str = "career_profile.json"
    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = Field(0, ge=0, le=10)
    enable_uploads: bool = True
    metadata: Optional[Dict[str, Any]] = None


app = FastAPI(
    title="Resume Pipeline API",
    description="API for submitting resume generation jobs.",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {"message": "Resume Pipeline API is running."}


@app.get("/jobs")
def list_jobs():
    """
    List all available jobs.

    This endpoint scans the 'jobs' directory and returns a summary of each
    job JSON file found.
    """
    jobs_dir = Path("jobs")
    if not jobs_dir.exists():
        return []

    job_list = []
    for job_file in jobs_dir.glob("*.json"):
        if job_file.name == "schema.json":
            continue

        try:
            with open(job_file, "r") as f:
                job_data = json.load(f)
                job_details = job_data.get("job_details", {})
                job_list.append(
                    {
                        "job_id": job_file.stem,
                        "company": job_details.get("company", "Unknown"),
                        "job_title": job_details.get("job_title", "Unknown"),
                    }
                )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not parse {job_file.name}: {e}")
            # Add to list with partial info
            job_list.append(
                {
                    "job_id": job_file.stem,
                    "company": "Invalid Format",
                    "job_title": "Invalid Format",
                }
            )

    return job_list


@app.post("/jobs/{job_id}/submit", status_code=202)
def resubmit_job(job_id: str, request: ResubmitJobRequest):
    """
    Resubmit an existing job.

    This endpoint finds a job by its ID and submits it to the pipeline again
    with the provided options.
    """
    logger.info(f"Received request to resubmit job: {job_id}")

    # Find the job JSON file
    job_json_path = Path("jobs") / f"{job_id}.json"
    if not job_json_path.exists():
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

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
        logger.info(f"Successfully resubmitted job {job_id} as {published_job_id}")

        return {
            "message": "Job resubmitted successfully",
            "new_job_id": published_job_id,
            "original_job_id": job_id,
        }
    except Exception as e:
        logger.error(f"Failed to resubmit job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/jobs", status_code=201)
def submit_job(request: ApiJobRequest):
    """
    Submit a new resume generation job.

    This endpoint accepts job details in a JSON format, saves it to a file,
    and publishes a job request to the RabbitMQ queue.
    """
    job_id = f"api-job-{uuid.uuid4()}"
    logger.info(f"Received job submission: {job_id}")

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
        published_job_id = publish_job_request(
            job_json_path=str(job_json_path),
            career_profile_path=request.career_profile_path,
            template=request.template,
            output_backend=request.output_backend,
            priority=request.priority,
            enable_uploads=request.enable_uploads,
            metadata=request.metadata,
        )
        logger.info(f"Successfully published job {published_job_id} to RabbitMQ")

        return {
            "message": "Job submitted successfully",
            "job_id": published_job_id,
            "job_json_path": str(job_json_path),
        }

    except FileNotFoundError as e:
        logger.error(f"File not found error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file path: {e.filename}",
        )
    except Exception as e:
        logger.error(f"Failed to submit job {job_id}: {e}")
        # Clean up created job file if something goes wrong
        if job_json_path.exists():
            job_json_path.unlink()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    # --- Job Status Monitoring (SSE) ---


async def status_event_generator(job_id: Optional[str] = None):
    """
    Yields server-sent events for job status updates.
    """
    q = queue.Queue()

    def consumer_callback(channel, method, properties, body):
        """Callback to put messages in the queue."""
        q.put(body)
        status = json.loads(body)
        if job_id and status.get("status") in ["job_completed", "job_failed"]:
            # If monitoring a single job and it has finished, stop consuming
            channel.stop_consuming()

    def start_consumer():
        """Connects to RabbitMQ and starts consuming messages."""
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

            logger.info(f"SSE consumer started for job_id: {job_id or 'all'}")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"SSE consumer RabbitMQ connection error: {e}")
            q.put(json.dumps({"error": "RabbitMQ connection failed"}).encode())
        except Exception as e:
            logger.error(f"SSE consumer error: {e}")
            q.put(json.dumps({"error": str(e)}).encode())
        finally:
            if "channel" in locals() and channel.is_open:
                channel.close()
            if "connection" in locals() and connection.is_open:
                connection.close()
            logger.info(f"SSE consumer stopped for job_id: {job_id or 'all'}")
            q.put(None)  # Signal that the consumer has stopped

    # Run the consumer in a separate thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    try:
        while True:
            # Wait for a message from the queue
            if consumer_thread.is_alive():
                try:
                    message_body = await asyncio.to_thread(q.get, timeout=1)
                except queue.Empty:
                    # Send a keep-alive comment if no message received
                    yield {"event": "ping", "data": ""}
                    continue
            else:  # if thread is dead
                try:
                    message_body = q.get_nowait()
                except queue.Empty:
                    break

            if message_body is None:
                break  # Consumer has stopped

            status = json.loads(message_body)

            # If a job_id is specified, filter messages
            if job_id and status.get("job_id") != job_id:
                continue

            yield {"event": "message", "data": json.dumps(status)}

    except asyncio.CancelledError:
        logger.info("SSE client disconnected.")
        # The thread will exit on its own as it is a daemon thread
    finally:
        logger.info("SSE generator finished.")


@app.get("/jobs/status")
async def stream_all_jobs_status():
    """
    Stream status updates for all jobs using Server-Sent Events.
    """
    return EventSourceResponse(status_event_generator())


@app.get("/jobs/{job_id}/status")
async def stream_job_status(job_id: str):
    """
    Stream status updates for a specific job using Server-Sent Events.
    """
    return EventSourceResponse(status_event_generator(job_id=job_id))
