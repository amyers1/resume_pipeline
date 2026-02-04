import asyncio
import json
import logging
from datetime import datetime

import aio_pika
from fastapi import FastAPI, HTTPException
from s3_manager import s3_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LaTeX Service API")


# RabbitMQ Publishing Logic
async def publish_latex_compile_request(
    job_id: str, content: str, filename: str, engine: str, create_backup: bool
):
    """Async helper to publish a LaTeX compilation request."""
    from config import settings

    connection = await aio_pika.connect_robust(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        login=settings.rabbitmq_user,
        password=settings.rabbitmq_pass,
    )
    async with connection:
        channel = await connection.channel()
        payload = {
            "job_id": job_id,
            "content": content,
            "filename": filename,
            "engine": engine,
            "create_backup": create_backup,
        }
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=settings.latex_compile_queue,
        )
        logger.info(f"📨 Published LaTeX Compile Request for Job {job_id}")


@app.post("/jobs/{job_id}/compile")
async def compile_latex(job_id: str, request: dict):
    """
    Request LaTeX compilation via RabbitMQ.
    """
    await publish_latex_compile_request(
        job_id=job_id,
        content=request["content"],
        filename=request.get("filename", "resume.tex"),
        engine=request.get("engine", "xelatex"),
        create_backup=request.get("create_backup", True),
    )
    return {"message": "Compilation request submitted", "job_id": job_id}


@app.get("/jobs/{job_id}/source")
async def get_latex_source(job_id: str):
    """Get LaTeX source from S3."""
    s3_key = f"{job_id}/resume.tex"
    content = await asyncio.to_thread(s3_manager.get_bytes, s3_key)

    if not content:
        raise HTTPException(status_code=404, detail="LaTeX source not found")

    return {"job_id": job_id, "content": content.decode("utf-8"), "s3_key": s3_key}


@app.put("/jobs/{job_id}/source")
async def save_latex_source(job_id: str, request: dict):
    """Save LaTeX source to S3 (without compiling)."""
    s3_key = f"{job_id}/resume.tex"
    content = request["content"]

    # Create backup first
    if request.get("create_backup", True):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_key = f"{job_id}/backups/resume_backup_{timestamp}.tex"
        await asyncio.to_thread(
            s3_manager.upload_bytes,
            content.encode("utf-8"),
            backup_key,
            content_type="text/x-tex",
        )

    # Save current version
    success = await asyncio.to_thread(
        s3_manager.upload_bytes,
        content.encode("utf-8"),
        s3_key,
        content_type="text/x-tex",
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save to S3")

    return {"success": True, "job_id": job_id, "s3_key": s3_key}


@app.get("/jobs/{job_id}/backups")
async def list_latex_backups(job_id: str):
    """List backup versions from S3."""
    versions = await asyncio.to_thread(s3_manager.list_versions, job_id)
    return versions
