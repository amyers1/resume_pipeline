"""
RabbitMQ Worker for Resume Pipeline

This worker consumes job requests from RabbitMQ and executes the resume generation pipeline.
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from resume_pipeline_rabbitmq import (
    JobRequest,
    JobStatus,
    MessageType,
    PipelineProgressTracker,
    PipelineStage,
    RabbitMQClient,
    RabbitMQConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResumePipelineWorker:
    """Worker that processes resume generation jobs from RabbitMQ."""

    def __init__(self, enable_rabbitmq: bool = True):
        self.enable_rabbitmq = enable_rabbitmq
        self.rabbitmq_client: Optional[RabbitMQClient] = None

        if enable_rabbitmq:
            self.rabbitmq_client = RabbitMQClient()
            if not self.rabbitmq_client.connect():
                logger.warning(
                    "Failed to connect to RabbitMQ - running in standalone mode"
                )
                self.enable_rabbitmq = False

    def process_job(self, job_request: JobRequest):
        """
        Process a single job request.

        This method:
        1. Updates .env with job parameters
        2. Imports and runs the pipeline
        3. Publishes progress updates
        4. Publishes completion/error status
        """
        started_at = datetime.utcnow().isoformat()
        tracker = None

        if self.enable_rabbitmq:
            tracker = PipelineProgressTracker(self.rabbitmq_client, job_request.job_id)

            # Publish job started
            status = JobStatus(
                job_id=job_request.job_id,
                status=MessageType.JOB_STARTED,
                message="Job started",
                started_at=started_at,
            )
            self.rabbitmq_client.publish_job_status(status)

        try:
            logger.info(f"Starting job {job_request.job_id}")
            logger.info(f"  Job JSON: {job_request.job_json_path}")
            logger.info(f"  Career Profile: {job_request.career_profile_path}")
            logger.info(f"  Template: {job_request.template}")
            logger.info(f"  Backend: {job_request.output_backend}")

            # Update environment with job parameters
            self._update_env(job_request)

            # Import pipeline components
            # Note: Import here to pick up updated .env values
            from resume_pipeline.config import PipelineConfig
            from resume_pipeline.pipeline import ResumePipeline

            # Create config (reads from .env)
            config = PipelineConfig()

            # Create pipeline with progress tracking
            pipeline = self._create_pipeline_with_tracking(config, tracker)

            # Run the pipeline
            structured_resume, latex_output, pdf_path = pipeline.run()

            # Collect output files
            output_files = self._collect_output_files(config, structured_resume)

            # Publish completion
            if self.enable_rabbitmq:
                self.rabbitmq_client.publish_completion(
                    job_request.job_id,
                    output_files,
                    started_at,
                    f"Resume generated successfully for {structured_resume.full_name}",
                )

            logger.info(f"Job {job_request.job_id} completed successfully")
            logger.info(f"  Output directory: {config.output_dir}")

        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            logger.error(f"Job {job_request.job_id} failed: {error_msg}")
            logger.error(error_trace)

            # Publish error
            if self.enable_rabbitmq:
                stage = tracker.current_stage if tracker else None
                self.rabbitmq_client.publish_error(
                    job_request.job_id, error_msg, started_at, stage
                )

    def _update_env(self, job_request: JobRequest):
        """Update environment variables based on job request."""
        os.environ["JOB_JSON_PATH"] = job_request.job_json_path
        os.environ["CAREER_PROFILE_PATH"] = job_request.career_profile_path

        if job_request.template:
            if job_request.output_backend == "latex":
                os.environ["LATEX_TEMPLATE"] = job_request.template
            # For weasyprint, template might map to CSS file

        os.environ["OUTPUT_BACKEND"] = job_request.output_backend

        # Disable/enable uploads based on job request
        enable_uploads = "true" if job_request.enable_uploads else "false"
        os.environ["ENABLE_NEXTCLOUD"] = os.environ.get(
            "ENABLE_NEXTCLOUD", enable_uploads
        )
        os.environ["ENABLE_MINIO"] = os.environ.get("ENABLE_MINIO", enable_uploads)

    def _create_pipeline_with_tracking(self, config, tracker):
        """Create pipeline instance with RabbitMQ progress tracking."""
        from resume_pipeline.pipeline import ResumePipeline

        # Create base pipeline
        pipeline = ResumePipeline(config)

        # If RabbitMQ is enabled, wrap pipeline methods with progress tracking
        if tracker:
            pipeline = self._wrap_pipeline_with_tracking(pipeline, tracker)

        return pipeline

    def _wrap_pipeline_with_tracking(self, pipeline, tracker):
        """Wrap pipeline methods to publish progress updates."""
        original_run = pipeline.run

        def run_with_tracking():
            # Stage 1: Analyze JD
            tracker.start_stage(PipelineStage.ANALYZING_JD)
            # Original pipeline handles this internally

            # Let original run handle everything, but track progress
            # This is a simplified approach - for finer control, you'd wrap individual methods
            result = original_run()

            return result

        pipeline.run = run_with_tracking
        return pipeline

    def _collect_output_files(self, config, structured_resume) -> dict:
        """Collect paths to generated output files."""
        output_dir = config.output_dir
        company = (
            structured_resume.experience[0].company
            if structured_resume.experience
            else "unknown"
        )
        position = (
            structured_resume.experience[0].position
            if structured_resume.experience
            else "position"
        )

        # Sanitize filename
        filename_base = f"{company}_{position}".lower().replace(" ", "_")

        output_files = {
            "output_dir": str(output_dir),
            "structured_resume": str(output_dir / "structured_resume.json"),
        }

        # Check for LaTeX file
        tex_file = output_dir / f"{filename_base}.tex"
        if tex_file.exists():
            output_files["latex"] = str(tex_file)

        # Check for PDF file
        pdf_file = output_dir / f"{filename_base}.pdf"
        if pdf_file.exists():
            output_files["pdf"] = str(pdf_file)

        # Add checkpoint files
        for checkpoint in ["jd_requirements", "matched_achievements", "critique"]:
            checkpoint_file = output_dir / f"{checkpoint}.json"
            if checkpoint_file.exists():
                output_files[checkpoint] = str(checkpoint_file)

        return output_files

    def start(self):
        """Start the worker and begin consuming jobs."""
        if not self.enable_rabbitmq:
            logger.error("RabbitMQ is not enabled or connection failed")
            return

        logger.info("Starting Resume Pipeline Worker")
        logger.info(f"  RabbitMQ Host: {self.rabbitmq_client.config.host}")
        logger.info(f"  Job Queue: {self.rabbitmq_client.config.job_queue}")
        logger.info("")

        try:
            self.rabbitmq_client.consume_jobs(self.process_job)
        except KeyboardInterrupt:
            logger.info("Worker stopped by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            logger.error(traceback.format_exc())
        finally:
            if self.rabbitmq_client:
                self.rabbitmq_client.close()


def main():
    """Main entry point for the worker."""
    # Check if RabbitMQ should be enabled
    enable_rabbitmq = os.getenv("ENABLE_RABBITMQ", "true").lower() == "true"

    if not enable_rabbitmq:
        logger.info("RabbitMQ integration disabled (ENABLE_RABBITMQ=false)")
        return

    # Create and start worker
    worker = ResumePipelineWorker(enable_rabbitmq=enable_rabbitmq)
    worker.start()


if __name__ == "__main__":
    main()
