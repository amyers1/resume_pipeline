"""
Resume Pipeline Worker - AsyncIO Compatible

Processes resume generation jobs from RabbitMQ queue with PostgreSQL backend.
Uses asyncio for RabbitMQ/DB IO and threads for CPU-bound Pipeline execution.
"""

import asyncio
import json
import logging
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from database import AsyncSessionLocal
from models import Job
from rabbitmq import (
    AsyncRabbitMQClient,
    JobRequest,
    MessageType,
    PipelineStage,
)
from resume_pipeline.config import PipelineConfig
from resume_pipeline.pipeline import ResumePipeline
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseResumeWorker:
    """
    Async Worker that processes resume generation jobs.
    """

    def __init__(self):
        """Initialize worker with Async RabbitMQ client."""
        self.rabbitmq = AsyncRabbitMQClient()
        self.loop = asyncio.get_event_loop()
        logger.info("Async Worker initialized")

    def _run_pipeline_sync(
        self, config: PipelineConfig, job_id: str, progress_queue: asyncio.Queue
    ):
        """
        Wrapper to run the synchronous ResumePipeline in a separate thread.
        Bridges the synchronous callback to the async event loop via a Queue or run_coroutine_threadsafe.
        """

        # Define the callback that runs in the THREAD
        def thread_callback(stage: str, percent: int, message: str):
            # Schedule the publish coroutine on the MAIN EVENT LOOP
            asyncio.run_coroutine_threadsafe(
                self.rabbitmq.publish_progress(job_id, stage, percent, message),
                self.loop,
            )

        try:
            pipeline = ResumePipeline(config)

            # Use the existing method in ResumePipeline to attach our bridge
            if hasattr(pipeline, "set_progress_callback"):
                pipeline.set_progress_callback(thread_callback)

            # BLOCKING CALL - Runs in thread
            return pipeline.run()
        except Exception as e:
            raise e

    async def process_job(self, request: JobRequest) -> None:
        """
        Process a single job request asynchronously.
        """
        logger.info(f"📥 Processing Job ID: {request.job_id}")

        async with AsyncSessionLocal() as db:
            try:
                # 1. Fetch Job (Async)
                result = await db.execute(select(Job).where(Job.id == request.job_id))
                job = result.scalars().first()

                if not job:
                    logger.error(f"❌ Job {request.job_id} not found in database")
                    return

                # 2. Update Status to Processing (Async)
                job.status = "processing"
                job.started_at = datetime.now(timezone.utc)
                await db.commit()

                await self.rabbitmq.publish_job_status(
                    job_id=job.id, status=MessageType.JOB_STARTED
                )

                # 3. Prepare Pipeline Config (CPU Bound - fast enough to run in loop)
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    # Generate temporary files for the pipeline logic
                    jd_path = temp_path / "job_description.json"
                    profile_path = temp_path / "career_profile.json"

                    # Note: job.to_schema_json() is synchronous Pydantic logic
                    reconstructed_json = job.to_schema_json()

                    with open(jd_path, "w", encoding="utf-8") as f:
                        json.dump(reconstructed_json, f, indent=2)

                    with open(profile_path, "w", encoding="utf-8") as f:
                        json.dump(job.career_profile_json, f, indent=2)

                    persistent_output = Path("output") / str(job.id)
                    persistent_output.mkdir(parents=True, exist_ok=True)

                    pipeline_overrides = {
                        "company_name": job.company,
                        "job_title": job.job_title,
                        "base_filename": f"{job.company}_{job.job_title}".replace(
                            " ", "_"
                        ),
                        "job_json_path": str(jd_path),
                        "career_profile_path": str(profile_path),
                        "latex_template": job.template,
                        "output_backend": job.output_backend,
                        "output_dir": persistent_output,
                        "use_flat_structure": True,
                    }

                    if job.advanced_settings:
                        pipeline_overrides.update(job.advanced_settings)

                    config = PipelineConfig.from_env(**pipeline_overrides)

                    # 4. Run Pipeline in Thread (Offload blocking work)
                    logger.info(
                        f"🚀 Starting pipeline for {job.company} - {job.job_title}"
                    )

                    # asyncio.to_thread runs the sync function in a separate thread
                    # while awaiting it here, allowing the loop to handle other events (like heartbeats)
                    start_time = datetime.now(timezone.utc)

                    # Pass a dummy queue if not using it, or handle callback logic inside wrapper
                    # The wrapper `_run_pipeline_sync` handles the callback bridging.
                    (
                        structured_resume,
                        output_artifact,
                        pdf_path,
                    ) = await asyncio.to_thread(
                        self._run_pipeline_sync, config, job.id, None
                    )

                    end_time = datetime.now(timezone.utc)
                    processing_time = (end_time - start_time).total_seconds()
                    logger.info(f"✅ Pipeline completed in {processing_time:.1f}s")

                    # 5. Collect Results
                    output_files = {}
                    if pdf_path and pdf_path.exists():
                        output_files["pdf"] = str(pdf_path)

                    for ext in [".tex", ".json", ".md"]:
                        files = list(persistent_output.glob(f"*{ext}"))
                        if files:
                            output_files[ext.lstrip(".")] = str(files[0])

                    # 6. Update Database (Async)
                    # We need to re-fetch or attach the job instance if the session expired,
                    # but usually with async session context it remains active.
                    job.status = "completed"
                    job.completed_at = end_time
                    job.processing_time_seconds = processing_time
                    job.output_files = output_files
                    if hasattr(structured_resume, "final_score"):
                        job.final_score = structured_resume.final_score

                    await db.commit()

                    await self.rabbitmq.publish_completion(
                        job_id=job.id,
                        output_files=output_files,
                        started_at=start_time.isoformat(),
                    )
                    logger.info(f"✅ Job {job.id} completed successfully")

            except Exception as e:
                # Error Handling
                error_msg = str(e)
                error_trace = traceback.format_exc()
                logger.error(f"❌ Pipeline failed: {error_msg}")
                logger.debug(error_trace)

                # Re-fetch job to ensure clean state for error update
                try:
                    result = await db.execute(
                        select(Job).where(Job.id == request.job_id)
                    )
                    job = result.scalars().first()
                    if job:
                        job.status = "failed"
                        job.completed_at = datetime.now(timezone.utc)
                        job.error_message = error_msg
                        await db.commit()

                        await self.rabbitmq.publish_error(
                            job_id=job.id,
                            error_msg=error_msg,
                            started_at=job.started_at.isoformat()
                            if job.started_at
                            else "",
                        )
                except Exception as db_err:
                    logger.error(f"Failed to update job error state: {db_err}")

    async def start(self) -> None:
        """
        Start the worker and begin consuming jobs from RabbitMQ.
        """
        logger.info("=" * 80)
        logger.info("Async Resume Pipeline Worker Starting")
        logger.info("=" * 80)

        Path("output").mkdir(exist_ok=True)

        try:
            await self.rabbitmq.connect()
            logger.info("✅ Ready to process jobs")

            # Start consuming
            # The callback `process_job` is async, so aio_pika will await it automatically
            await self.rabbitmq.consume_jobs(callback=self.process_job)

            # Keep the loop running
            # In a real app, consume_jobs might return a Future or we wait on a signal
            # aio_pika's start_consuming is blocking (but async compatible),
            # but our RabbitMQClient wrapper uses a non-blocking iterator approach usually.
            # If your RabbitMQClient.consume_jobs returns immediately (starts background task),
            # we need to wait here.
            # Based on previous refactor, consume_jobs awaits the iterator, so it blocks execution
            # (in a good way) until cancelled.

        except asyncio.CancelledError:
            logger.info("Worker cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal Worker Error: {e}")
            sys.exit(1)
        finally:
            await self.rabbitmq.close()


def main() -> None:
    """Main entry point for the worker."""
    import warnings

    warnings.filterwarnings("ignore", category=UserWarning)

    try:
        worker = DatabaseResumeWorker()
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        # Allow graceful exit on Ctrl+C
        pass
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
