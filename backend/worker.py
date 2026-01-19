"""
Resume Pipeline Worker - Python 3.14 Compatible

Processes resume generation jobs from RabbitMQ queue with PostgreSQL backend.
Updated for Python 3.14 compatibility with proper type hints.
"""

import json
import logging
import os
import sys
import tempfile
import traceback
from datetime import UTC, datetime
from pathlib import Path

from database import SessionLocal
from models import Job
from rabbitmq import (
    JobRequest,
    MessageType,
    PipelineStage,
    RabbitMQClient,
)
from resume_pipeline.config import PipelineConfig
from resume_pipeline.pipeline import ResumePipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseResumeWorker:
    """
    Worker that processes resume generation jobs from RabbitMQ.

    Reads job details from PostgreSQL, runs the resume pipeline,
    and updates job status back to the database.
    """

    def __init__(self):
        """Initialize worker with RabbitMQ client."""
        self.rabbitmq = RabbitMQClient()
        logger.info("Worker initialized")

    def process_job(self, request: JobRequest) -> None:
        """
        Process a single job request.

        Args:
            request: Job request from RabbitMQ queue
        """
        logger.info(f"📥 Processing Job ID: {request.job_id}")

        db = SessionLocal()

        try:
            job = db.query(Job).filter(Job.id == request.job_id).first()

            if not job:
                logger.error(f"❌ Job {request.job_id} not found in database")
                return

            # Update status to processing
            job.status = "processing"
            job.started_at = datetime.now(UTC)
            db.commit()

            # Publish job started event
            self.rabbitmq.publish_job_status(
                job_id=job.id, status=MessageType.JOB_STARTED
            )

            # Create temporary workspace for file-based pipeline
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                try:
                    # Generate job files from database
                    jd_path = temp_path / "job_description.json"
                    profile_path = temp_path / "career_profile.json"

                    # Reconstruct JSON from database columns
                    reconstructed_json = job.to_schema_json()

                    with open(jd_path, "w", encoding="utf-8") as f:
                        json.dump(reconstructed_json, f, indent=2)

                    with open(profile_path, "w", encoding="utf-8") as f:
                        json.dump(job.career_profile_json, f, indent=2)

                    # Define persistent output directory
                    persistent_output = Path("output") / str(job.id)
                    persistent_output.mkdir(parents=True, exist_ok=True)

                    # Configure pipeline with job settings
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

                    # Inject advanced settings from database if present
                    if job.advanced_settings:
                        pipeline_overrides.update(job.advanced_settings)

                    config = PipelineConfig.from_env(**pipeline_overrides)

                    # Create pipeline with progress callback
                    pipeline = ResumePipeline(config)

                    def progress_callback(
                        stage: str, percent: int, message: str
                    ) -> None:
                        """Callback for pipeline progress updates."""
                        logger.info(f"[{percent}%] {stage}: {message}")

                        # Map stage names to PipelineStage enum
                        stage_map = {
                            "analyzing_jd": PipelineStage.ANALYSIS,
                            "matching_achievements": PipelineStage.ANALYSIS,
                            "generating_draft": PipelineStage.GENERATING_DRAFT,
                            "critiquing": PipelineStage.CRITIQUE,
                            "refining": PipelineStage.REFINEMENT,
                            "generating_output": PipelineStage.FORMATTING,
                            "post_processing": PipelineStage.FORMATTING,
                        }

                        pipeline_stage = stage_map.get(
                            stage, PipelineStage.GENERATING_DRAFT
                        )

                        # Publish progress to RabbitMQ
                        self.rabbitmq.publish_progress(
                            job_id=job.id,
                            stage=pipeline_stage,
                            percent=percent,
                            message=message,
                        )

                    # Set progress callback if supported
                    if hasattr(pipeline, "set_progress_callback"):
                        pipeline.set_progress_callback(progress_callback)

                    # Run the pipeline
                    logger.info(
                        f"🚀 Starting pipeline for {job.company} - {job.job_title}"
                    )
                    start_time = datetime.now(UTC)

                    structured_resume, output_artifact, pdf_path = pipeline.run()

                    end_time = datetime.now(UTC)
                    processing_time = (end_time - start_time).total_seconds()

                    logger.info(f"✅ Pipeline completed in {processing_time:.1f}s")

                    # Collect output files
                    output_files = {}
                    if pdf_path and pdf_path.exists():
                        output_files["pdf"] = str(pdf_path)

                    # Find other generated files
                    for ext in [".tex", ".json", ".md"]:
                        files = list(persistent_output.glob(f"*{ext}"))
                        if files:
                            output_files[ext.lstrip(".")] = str(files[0])

                    # Update job in database
                    job.status = "completed"
                    job.completed_at = end_time
                    job.processing_time_seconds = processing_time
                    job.output_files = output_files

                    # Store final quality score if available
                    if hasattr(structured_resume, "final_score"):
                        job.final_score = structured_resume.final_score

                    db.commit()

                    # Publish completion event
                    self.rabbitmq.publish_completion(
                        job_id=job.id,
                        output_files=output_files,
                        started_at=start_time.isoformat(),
                    )

                    logger.info(f"✅ Job {job.id} completed successfully")

                except Exception as e:
                    # Handle pipeline errors
                    error_msg = str(e)
                    error_trace = traceback.format_exc()

                    logger.error(f"❌ Pipeline failed: {error_msg}")
                    logger.debug(error_trace)

                    # Update job with error
                    job.status = "failed"
                    job.completed_at = datetime.now(UTC)
                    job.error_message = error_msg

                    if job.started_at:
                        processing_time = (
                            datetime.now(UTC) - job.started_at
                        ).total_seconds()
                        job.processing_time_seconds = processing_time

                    db.commit()

                    # Publish error event
                    self.rabbitmq.publish_error(
                        job_id=job.id,
                        error_msg=error_msg,
                        started_at=job.started_at.isoformat() if job.started_at else "",
                    )

                    logger.error(f"❌ Job {job.id} failed after {processing_time:.1f}s")

        except Exception as e:
            logger.error(f"❌ Error processing job {request.job_id}: {e}")
            logger.debug(traceback.format_exc())

        finally:
            db.close()

    def start(self) -> None:
        """
        Start the worker and begin consuming jobs from RabbitMQ.

        This will run indefinitely until interrupted.
        """
        logger.info("=" * 80)
        logger.info("Resume Pipeline Worker Starting")
        logger.info("=" * 80)
        logger.info(
            f"RabbitMQ Host: {self.rabbitmq.config.host}:{self.rabbitmq.config.port}"
        )
        logger.info(f"Job Queue: {self.rabbitmq.config.job_queue}")
        logger.info(f"Status Queue: {self.rabbitmq.config.status_queue}")
        logger.info(f"Progress Queue: {self.rabbitmq.config.progress_queue}")
        logger.info("=" * 80)

        # Ensure output directory exists
        Path("output").mkdir(exist_ok=True)

        # Connect to RabbitMQ
        if not self.rabbitmq.connect():
            logger.error("❌ Failed to connect to RabbitMQ")
            sys.exit(1)

        logger.info("✅ Connected to RabbitMQ")

        # Start consuming jobs
        try:
            logger.info("👀 Waiting for jobs...")
            self.rabbitmq.consume_jobs(callback=self.process_job)
        except KeyboardInterrupt:
            logger.info("\n⚠️  Worker interrupted by user")
        except Exception as e:
            logger.error(f"❌ Worker error: {e}")
            logger.debug(traceback.format_exc())
        finally:
            logger.info("🛑 Shutting down worker...")
            if hasattr(self.rabbitmq, "close"):
                self.rabbitmq.close()
            logger.info("✅ Worker shut down gracefully")


def main() -> None:
    """Main entry point for the worker."""
    # Suppress Pydantic v1 warning from LangChain
    import warnings

    warnings.filterwarnings(
        "ignore",
        message="Core Pydantic V1 functionality isn't compatible with Python 3.14",
        category=UserWarning,
    )

    try:
        worker = DatabaseResumeWorker()
        worker.start()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
