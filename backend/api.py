import asyncio
import json
import logging
import threading
import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from .database import Base, engine, get_db
from .models import Job, JobListResponse, JobResponse, JobSubmitRequest
from .rabbitmq import (
    RabbitMQClient,
    RabbitMQConfig,
    publish_job_request,
)

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Pipeline API")

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
    """
    Singleton that manages client connections and broadcasts
    RabbitMQ messages to all of them.
    """

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
        # Clean out stale connections while broadcasting
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
        # Consume both status and progress queues
        client.channel.basic_consume(
            queue=config.status_queue, on_message_callback=on_message, auto_ack=True
        )
        client.channel.basic_consume(
            queue=config.progress_queue, on_message_callback=on_message, auto_ack=True
        )
        client.channel.start_consuming()
    except Exception as e:
        logger.error(f"RabbitMQ consumer failed: {e}")


# ==========================
# API ENDPOINTS
# ==========================


@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()
    # Start consumer in background thread
    t = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    t.start()


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
        # Worker will fetch data from DB, so we don't need to pass paths
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

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


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
