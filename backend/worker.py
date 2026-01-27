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
from models import CareerExperience, CareerProfile, Job
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
from sqlalchemy.orm import selectinload

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
        self.loop = None  # Loop is initialized in start()
        logger.info("Async Worker initialized")

    def _run_pipeline_sync(
        self, config: PipelineConfig, job_id: str, loop: asyncio.AbstractEventLoop
    ):
        """
        Wrapper to run the synchronous ResumePipeline in a separate thread.
        Bridges the synchronous callback to the async event loop via run_coroutine_threadsafe.
        """

        # Define the callback that runs in the THREAD
        def thread_callback(stage: str, percent: int, message: str):
            # Schedule the publish coroutine on the MAIN EVENT LOOP
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.rabbitmq.publish_progress(job_id, stage, percent, message),
                    loop,
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

        # Extract data we need outside the session
        job_id = request.job_id
        company = None
        job_title = None
        template = None
        output_backend = None
        advanced_settings = None
        job_data = None
        profile_data = None
        start_time = None

        async with AsyncSessionLocal() as db:
            try:
                # 1. Fetch Job
                result = await db.execute(select(Job).where(Job.id == job_id))
                job = result.scalars().first()

                if not job:
                    logger.error(f"❌ Job {job_id} not found in database")
                    return

                # 2. Fetch Career Profile
                result = await db.execute(
                    select(CareerProfile)
                    .where(CareerProfile.user_id == job.user_id)
                    .order_by(CareerProfile.updated_at.desc())
                    .options(
                        selectinload(CareerProfile.experience).selectinload(
                            CareerExperience.highlights
                        ),
                        selectinload(CareerProfile.education),
                        selectinload(CareerProfile.projects),
                        selectinload(CareerProfile.certifications),
                    )
                )
                career_profile = result.scalars().first()

                if not career_profile:
                    logger.error(f"❌ No career profile found for user {job.user_id}")
                    job.status = "failed"
                    job.error_message = "No career profile found for user"
                    await db.commit()
                    return

                # 3. Extract ALL data as plain dicts/values BEFORE leaving the session
                job_data = job.to_schema_json()
                profile_data = career_profile.to_full_json()
                company = job.company
                job_title = job.job_title
                template = job.template
                output_backend = job.output_backend
                advanced_settings = job.advanced_settings

                # 4. Update Status
                job.status = "processing"
                job.started_at = datetime.now(timezone.utc)
                start_time = job.started_at
                await db.commit()

            except Exception as e:
                logger.error(f"❌ Database error: {e}")
                logger.debug(traceback.format_exc())
                return

        # 5. NOW we're outside the async session - safe to create config and run pipeline
        try:
            await self.rabbitmq.publish_job_status(
                job_id=job_id, status=MessageType.JOB_STARTED
            )

            persistent_output = Path("output") / str(job_id)
            persistent_output.mkdir(parents=True, exist_ok=True)

            pipeline_overrides = {
                "company_name": company,
                "job_title": job_title,
                "base_filename": f"{company}_{job_title}".replace(" ", "_"),
                "job_json_path": job_data,
                "career_profile_path": profile_data,
                "latex_template": template,
                "output_backend": output_backend,
                "output_dir": persistent_output,
                "use_flat_structure": True,
            }

            if advanced_settings:
                pipeline_overrides.update(advanced_settings)

            config = PipelineConfig.from_env(**pipeline_overrides)

            # 6. Run Pipeline in Thread
            logger.info(f"🚀 Starting pipeline for {company} - {job_title}")

            (
                structured_resume,
                output_artifact,
                pdf_path,
            ) = await asyncio.to_thread(
                self._run_pipeline_sync, config, job_id, self.loop
            )

            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            logger.info(f"✅ Pipeline completed in {processing_time:.1f}s")

            # 7. Collect Results
            output_files = {}
            if pdf_path and pdf_path.exists():
                output_files["pdf"] = str(pdf_path)

            for ext in [".tex", ".json", ".md"]:
                files = list(persistent_output.glob(f"*{ext}"))
                if files:
                    output_files[ext.lstrip(".")] = str(files[0])

            # 8. Update Database with success (new session)
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Job).where(Job.id == job_id))
                job = result.scalars().first()

                if job:
                    job.status = "completed"
                    job.completed_at = end_time
                    job.processing_time_seconds = processing_time
                    job.output_files = output_files
                    if hasattr(structured_resume, "final_score"):
                        job.final_score = structured_resume.final_score
                    await db.commit()

            await self.rabbitmq.publish_completion(
                job_id=job_id,
                output_files=output_files,
                started_at=start_time.isoformat(),
            )
            logger.info(f"✅ Job {job_id} completed successfully")

        except Exception as e:
            # Pipeline execution error
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"❌ Pipeline failed: {error_msg}")
            logger.debug(error_trace)

            # Update job with error (new session)
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Job).where(Job.id == job_id))
                job = result.scalars().first()

                if job:
                    job.status = "failed"
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_message = error_msg
                    await db.commit()

                    await self.rabbitmq.publish_error(
                        job_id=job_id,
                        error_msg=error_msg,
                        started_at=start_time.isoformat() if start_time else "",
                    )

    async def start(self) -> None:
        """
        Start the worker and begin consuming jobs from RabbitMQ.
        """
        logger.info("=" * 80)
        logger.info("Async Resume Pipeline Worker Starting")
        logger.info("=" * 80)

        # CAPTURE LOOP HERE - Inside the async context
        self.loop = asyncio.get_running_loop()

        Path("output").mkdir(exist_ok=True)

        try:
            await self.rabbitmq.connect()
            logger.info("✅ Ready to process jobs")

            # Start consuming
            await self.rabbitmq.consume_jobs(callback=self.process_job)

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
        pass
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
