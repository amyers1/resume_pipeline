"""
Resume Pipeline Worker
Processes resume generation jobs from RabbitMQ queue using the resume_pipeline module.

This worker:
- Consumes JobRequest messages from resume.jobs queue
- Runs the full resume generation pipeline
- Publishes progress updates to resume.progress queue
- Publishes completion/failure events to resume.status queue
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add the resume_pipeline module to the path
sys.path.insert(0, str(Path(__file__).parent))

from resume_pipeline_rabbitmq import (
    JobRequest,
    MessageType,
    PipelineStage,
    RabbitMQClient,
    RabbitMQConfig,
)

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


class ResumeWorker:
    """Worker that processes resume generation jobs from RabbitMQ."""

    def __init__(self, rabbitmq_config: Optional[RabbitMQConfig] = None):
        """
        Initialize the resume worker.

        Args:
            rabbitmq_config: Optional RabbitMQ configuration. If None, uses defaults.
        """
        self.config = rabbitmq_config or RabbitMQConfig()
        self.client = RabbitMQClient(self.config)
        self.pipeline = None  # Will be lazily initialized

    def _get_pipeline(self):
        """Lazily initialize the resume pipeline."""
        if self.pipeline is None:
            try:
                from resume_pipeline.config import PipelineConfig
                from resume_pipeline.pipeline import ResumePipeline

                # Create a base config - we'll override per job
                self.pipeline_config_class = PipelineConfig
                self.pipeline_class = ResumePipeline
                logger.info("Resume pipeline modules loaded successfully")
            except ImportError as e:
                logger.error(f"Failed to import resume_pipeline: {e}")
                logger.error("Make sure resume_pipeline package is in PYTHONPATH")
                raise
        return self.pipeline_class, self.pipeline_config_class

    def update_job_metadata(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update job metadata file.

        Args:
            job_id: The job ID
            updates: Dictionary of updates to apply

        Returns:
            True if successful, False otherwise
        """
        metadata_path = JOBS_DIR / f"{job_id}_metadata.json"

        if not metadata_path.exists():
            logger.warning(f"Metadata file not found for job {job_id}")
            # Create new metadata if it doesn't exist
            metadata = {
                "job_id": job_id,
                "created_at": datetime.now(UTC).isoformat() + "Z",
            }
        else:
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read metadata for job {job_id}: {e}")
                return False

        # Apply updates
        metadata.update(updates)

        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Updated metadata for job {job_id}: {updates}")
            return True
        except Exception as e:
            logger.error(f"Failed to write metadata for job {job_id}: {e}")
            return False

    def process_job(self, job_request: JobRequest) -> bool:
        """
        Process a single resume generation job.

        Args:
            job_request: The job request to process

        Returns:
            True if successful, False otherwise
        """
        job_id = job_request.job_id
        start_time = time.time()
        started_at = datetime.now(UTC).isoformat()

        logger.info(f"Starting job {job_id}")
        logger.info(f"  Job file: {job_request.job_json_path}")
        logger.info(f"  Profile: {job_request.career_profile_path}")
        logger.info(f"  Template: {job_request.template}")
        logger.info(f"  Backend: {job_request.output_backend}")

        # Publish job started event
        self.client.publish_message(
            routing_key="resume.status.job_started",
            message={
                "job_id": job_id,
                "status": MessageType.JOB_STARTED.value,
                "started_at": started_at,
                "message": "Job processing started",
            },
        )

        # Update local metadata
        self.update_job_metadata(
            job_id,
            {
                "status": "processing",
                "started_at": started_at,
                "template": job_request.template,
                "output_backend": job_request.output_backend,
            },
        )

        try:
            # Validate files exist
            job_json_path = Path(job_request.job_json_path)
            if not job_json_path.exists():
                raise FileNotFoundError(f"Job file not found: {job_json_path}")

            career_profile_path = Path(job_request.career_profile_path)
            if not career_profile_path.exists():
                raise FileNotFoundError(
                    f"Career profile not found: {career_profile_path}"
                )

            # Read job data to get company and job title
            with open(job_json_path, "r") as f:
                job_data = json.load(f)

            company = job_data.get("job_details", {}).get("company", "Unknown")
            job_title = job_data.get("job_details", {}).get("job_title", "Unknown")
            base_file_name = f"{company}_{job_title}"

            logger.info(f"Processing: {company} - {job_title}")

            # Load pipeline modules
            ResumePipeline, PipelineConfig = self._get_pipeline()

            # Create output directory
            timestamp = datetime.now().strftime("%Y%m%d")
            run_timestamp = datetime.now().strftime("%H%M%S")
            output_dir = OUTPUT_DIR / timestamp / f"run_{run_timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Output directory: {output_dir}")

            # Update metadata with output directory
            self.update_job_metadata(job_id, {"output_dir": str(output_dir.absolute())})

            # Create pipeline configuration using from_env()
            # This loads from .env and we override with job-specific values
            pipeline_config = PipelineConfig.from_env(
                company, job_title, base_file_name, job_json_path=str(job_json_path)
            )

            # Override config with job-specific values
            pipeline_config.career_profile_path = career_profile_path
            pipeline_config.output_dir = output_dir
            pipeline_config.output_backend = job_request.output_backend

            # Map template to the appropriate config fields
            if job_request.output_backend == "latex":
                pipeline_config.latex_template = job_request.template
            else:
                # For weasyprint, template is mapped to template_name
                # The template parameter might be "awesome-cv" or "modern-deedy"
                # We'll set it appropriately
                pipeline_config.template_name = (
                    "resume.html.j2"  # Default HTML template
                )

            # Set upload configuration
            if hasattr(pipeline_config, "enable_minio"):
                pipeline_config.enable_minio = job_request.enable_uploads
            if hasattr(pipeline_config, "enable_nextcloud"):
                pipeline_config.enable_nextcloud = job_request.enable_uploads

            # Initialize pipeline
            pipeline = ResumePipeline(pipeline_config)

            # Define progress callback to publish updates
            def progress_callback(stage: str, percent: int, message: str = ""):
                """Callback to publish progress updates."""
                # Map stage names to PipelineStage enum
                stage_map = {
                    "analyzing_jd": PipelineStage.ANALYZING_JD,
                    "matching_achievements": PipelineStage.MATCHING_ACHIEVEMENTS,
                    "generating_draft": PipelineStage.GENERATING_DRAFT,
                    "critiquing": PipelineStage.CRITIQUING,
                    "refining": PipelineStage.REFINING,
                    "generating_output": PipelineStage.GENERATING_OUTPUT,
                    "post_processing": PipelineStage.POST_PROCESSING,
                }

                pipeline_stage = stage_map.get(stage, PipelineStage.GENERATING_DRAFT)

                self.client.publish_progress(
                    job_id=job_id,
                    stage=pipeline_stage,
                    percent=percent,
                    message=message or f"Processing: {stage}",
                )

                logger.info(f"Progress: {stage} - {percent}% - {message}")

            # Attach progress callback to pipeline if supported
            if hasattr(pipeline, "set_progress_callback"):
                pipeline.set_progress_callback(progress_callback)

            # Publish initial progress
            progress_callback("analyzing_jd", 0, "Starting job analysis")

            # Run the pipeline
            logger.info("Running resume generation pipeline...")

            structured_resume, output_artifact, pdf_path = pipeline.run()

            logger.info("Pipeline completed successfully")

            # Calculate processing time
            processing_time = time.time() - start_time

            # Collect output files
            output_files = {
                "output_dir": str(output_dir.absolute()),
            }

            if pdf_path:
                output_files["pdf"] = str(pdf_path.absolute())

            # Find other output files
            for ext in [".tex", ".json", ".txt"]:
                matching_files = list(output_dir.glob(f"*{ext}"))
                if matching_files:
                    output_files[ext.lstrip(".")] = str(matching_files[0].absolute())

            # Try to extract final score from critique.json
            final_score = None
            critique_file = output_dir / "checkpoint_critique.json"
            if critique_file.exists():
                try:
                    with open(critique_file, "r") as f:
                        critique_data = json.load(f)
                    # Extract score from various possible locations
                    for key in ["final_score", "score", "overall_score", "rating"]:
                        if key in critique_data:
                            final_score = float(critique_data[key])
                            break
                except Exception as e:
                    logger.warning(f"Failed to extract score from critique: {e}")

            # Update metadata with completion
            self.update_job_metadata(
                job_id,
                {
                    "status": "completed",
                    "completed_at": datetime.now(UTC).isoformat() + "Z",
                    "processing_time_seconds": round(processing_time, 2),
                    "final_score": final_score,
                    "output_files": output_files,
                    "company": company,
                    "job_title": job_title,
                },
            )

            # Publish completion event
            self.client.publish_completion(
                job_id=job_id,
                output_files=output_files,
                started_at=started_at,
                message=f"Resume generated successfully for {company} - {job_title}",
            )

            logger.info(
                f"Job {job_id} completed successfully in {processing_time:.2f}s"
            )
            logger.info(f"Final score: {final_score}")
            logger.info(f"Output: {output_dir}")

            return True

        except Exception as e:
            # Calculate processing time
            processing_time = time.time() - start_time
            error_msg = str(e)
            error_trace = traceback.format_exc()

            logger.error(f"Job {job_id} failed after {processing_time:.2f}s")
            logger.error(f"Error: {error_msg}")
            logger.error(f"Traceback:\n{error_trace}")

            # Update metadata with failure
            self.update_job_metadata(
                job_id,
                {
                    "status": "failed",
                    "error": error_msg,
                    "error_trace": error_trace,
                    "completed_at": datetime.now(UTC).isoformat() + "Z",
                    "processing_time_seconds": round(processing_time, 2),
                },
            )

            # Publish error event
            self.client.publish_error(
                job_id=job_id,
                error=error_msg,
                started_at=started_at,
                stage=PipelineStage.GENERATING_DRAFT,  # Default stage
            )

            return False

    def start(self):
        """Start consuming and processing jobs from the queue."""
        logger.info("Resume Pipeline Worker starting...")
        logger.info(f"RabbitMQ Host: {self.config.host}:{self.config.port}")
        logger.info(f"Job Queue: {self.config.job_queue}")
        logger.info(f"Status Queue: {self.config.status_queue}")
        logger.info(f"Progress Queue: {self.config.progress_queue}")
        logger.info(f"Error Queue: {self.config.error_queue}")

        # Ensure directories exist
        JOBS_DIR.mkdir(exist_ok=True)
        OUTPUT_DIR.mkdir(exist_ok=True)
        PROFILES_DIR.mkdir(exist_ok=True)

        # Connect to RabbitMQ
        if not self.client.connect():
            logger.error("Failed to connect to RabbitMQ")
            sys.exit(1)

        # Start consuming jobs
        try:
            self.client.consume_jobs(callback=self.process_job)
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            traceback.print_exc()
        finally:
            self.client.close()
            logger.info("Worker shut down")


def main():
    """Main entry point for the worker."""
    # Create worker with default config (reads from environment)
    worker = ResumeWorker()

    # Start processing jobs
    worker.start()


if __name__ == "__main__":
    main()
