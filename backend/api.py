import asyncio
import json
import logging
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from database import Base, engine, get_db
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from models import Job, JobListResponse, JobResponse, JobSubmitRequest
from rabbitmq import RabbitMQClient, RabbitMQConfig, publish_job_request
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Pipeline API")

# Directories
OUTPUT_DIR = Path("output")
PROFILES_DIR = Path("profiles")
TEMPLATES_DIR = Path("templates")

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
PROFILES_DIR.mkdir(exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# SSE BROADCASTER
# ==========================


class SSEBroadcaster:
    def __init__(self):
        self.connections: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def connect(self):
        queue = asyncio.Queue()
        async with self._lock:
            self.connections.append(queue)
        return queue

    async def disconnect(self, queue):
        async with self._lock:
            if queue in self.connections:
                self.connections.remove(queue)

    async def broadcast(self, message: dict):
        disconnected = []
        async with self._lock:
            for queue in self.connections:
                try:
                    await queue.put(json.dumps(message))
                except Exception:
                    disconnected.append(queue)

            for q in disconnected:
                self.connections.remove(q)


broadcaster = SSEBroadcaster()


# Background RabbitMQ Consumer
def start_rabbitmq_consumer():
    """Runs in a separate thread to consume RabbitMQ messages."""
    global loop
    config = RabbitMQConfig()

    def on_message(channel, method, properties, body):
        try:
            data = json.loads(body)
            # Schedule the broadcast in the main event loop
            asyncio.run_coroutine_threadsafe(broadcaster.broadcast(data), loop)
        except Exception as e:
            logger.error(f"Broadcast error: {e}")

    try:
        client = RabbitMQClient(config)
        client.connect()
        client.channel.basic_consume(
            queue=config.status_queue, on_message_callback=on_message, auto_ack=True
        )
        client.channel.basic_consume(
            queue=config.progress_queue, on_message_callback=on_message, auto_ack=True
        )
        # Also listen for completion/errors
        # (Assuming your routing keys are set up to duplicate these to status_queue or similar)

        client.channel.start_consuming()
    except Exception as e:
        logger.error(f"RabbitMQ consumer failed: {e}")


@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()
    t = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    t.start()


# ==========================
# SYSTEM ENDPOINTS
# ==========================


@app.get("/health")
def health_check():
    """Health check endpoint for frontend and orchestration."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/events")
async def sse_events():
    """Unified SSE stream for all clients."""
    queue = await broadcaster.connect()

    async def event_generator():
        try:
            while True:
                msg = await queue.get()
                yield {"data": msg}
        except asyncio.CancelledError:
            await broadcaster.disconnect(queue)

    return EventSourceResponse(event_generator())


# ==========================
# JOB ENDPOINTS
# ==========================


@app.post("/jobs", response_model=JobResponse, status_code=201)
def submit_job(request: JobSubmitRequest, db: Session = Depends(get_db)):
    """Submit a new job to DB and Queue."""
    job_id = str(uuid.uuid4())

    # 1. Save to Postgres
    new_job = Job(
        id=job_id,
        company=request.job_data.get("job_details", {}).get("company", "Unknown"),
        job_title=request.job_data.get("job_details", {}).get("job_title", "Unknown"),
        job_description_json=request.job_data,
        career_profile_json=request.career_profile_data,
        template=request.template,
        output_backend=request.output_backend,
        priority=request.priority,
        status="queued",
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # 2. Publish ID to RabbitMQ
    publish_job_request(
        job_id=job_id,
        job_json_path="DB",
        career_profile_path="DB",
        template=request.template,
        output_backend=request.output_backend,
        priority=request.priority,
    )

    return new_job


@app.get("/jobs", response_model=JobListResponse)
def list_jobs(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    """List jobs with efficient DB pagination."""
    skip = (page - 1) * size
    total = db.query(Job).count()
    jobs = db.query(Job).order_by(desc(Job.created_at)).offset(skip).limit(size).all()
    return {"items": jobs, "total": total, "page": page, "size": size}


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete files
    job_dir = OUTPUT_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)

    db.delete(job)
    db.commit()
    return {"status": "deleted"}


# ==========================
# FILE ENDPOINTS
# ==========================


@app.get("/jobs/{job_id}/files")
def list_job_files(job_id: str):
    """List generated files for a specific job."""
    job_dir = OUTPUT_DIR / job_id
    if not job_dir.exists():
        return []

    files = []
    for f in job_dir.glob("*"):
        if f.is_file():
            files.append(
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime),
                }
            )
    return files


@app.get("/jobs/{job_id}/files/{filename}")
def download_job_file(job_id: str, filename: str):
    """Download a specific artifact."""
    file_path = OUTPUT_DIR / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path, filename=filename, media_type="application/octet-stream"
    )


# ==========================
# PROFILE ENDPOINTS
# ==========================


@app.get("/profiles")
def list_profiles():
    """List available career profiles."""
    profiles = []
    for f in PROFILES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            profiles.append(
                {
                    "filename": f.name,
                    "name": data.get("name", "Unknown"),
                    "email": data.get("email", ""),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime),
                }
            )
        except Exception:
            continue
    return profiles


@app.post("/profiles")
async def upload_profile(file: UploadFile = File(...)):
    """Upload a new career profile JSON."""
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files allowed")

    file_path = PROFILES_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": file.filename, "status": "uploaded"}


@app.delete("/profiles/{filename}")
def delete_profile(filename: str):
    file_path = PROFILES_DIR / filename
    if file_path.exists():
        file_path.unlink()
    return {"status": "deleted"}


# ==========================
# TEMPLATE ENDPOINTS
# ==========================


@app.get("/job-templates")
def list_job_templates():
    """List available resume templates."""
    # This matches the structure expected by the frontend
    return [
        {"name": "Awesome CV", "filename": "awesome-cv", "type": "latex"},
        {"name": "Modern Deedy", "filename": "modern-deedy", "type": "latex"},
        {"name": "Standard HTML", "filename": "resume.html.j2", "type": "html"},
    ]
