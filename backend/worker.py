import json
import logging
import os
import shutil
import tempfile
import traceback
from datetime import UTC, datetime
from pathlib import Path

from rabbitmq import (
    JobRequest,
    RabbitMQClient,
    MessageType,
    PipelineStage,
)
from database import SessionLocal
from models import Job
from resume_pipeline.pipeline import ResumePipeline
from resume_pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)


class DatabaseResumeWorker:
    def __init__(self):
        self.rabbitmq = RabbitMQClient()

    def process_job(self, request: JobRequest):
        logger.info(f"Processing Job ID: {request.job_id}")

        db = SessionLocal()
        job = db.query(Job).filter(Job.id == request.job_id).first()

        if not job:
            logger.error(f"Job {request.job_id} not found in DB")
            return

        # Update Status: Processing
        job.status = "processing"
        job.started_at = datetime.now(UTC)
        db.commit()

        self.rabbitmq.publish_job_status(job_id=job.id, status=MessageType.JOB_STARTED)

        # Create a temporary workspace for the file-based pipeline
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                # 1. Materialize inputs to files (Pipeline expects files)
                jd_path = temp_path / "job_description.json"
                profile_path = temp_path / "career_profile.json"

                with open(jd_path, "w") as f:
                    json.dump(job.job_description_json, f)

                with open(profile_path, "w") as f:
                    json.dump(job.career_profile_json, f)

                # 2. Configure Pipeline
                # We use the existing Pipeline logic but point it to temp files
                config = PipelineConfig.from_env(
                    company_name=job.company,
                    job_title=job.job_title,
                    base_filename=f"{job.company}_{job.job_title}".replace(" ", "_"),
                    job_json_path=str(jd_path),
                )

                # Override with Job specific settings
                config.career_profile_path = profile_path
                config.latex_template = job.template
                config.output_backend = job.output_backend

                # Point output to a persistent location (e.g., volume mount or S3)
                # For now, we assume a local 'output' dir is mounted
                persistent_output = Path("output") / str(job.id)
                persistent_output.mkdir(parents=True, exist_ok=True)
                config.use_flat_structure = True  # <--- Add this
                config.output_dir = persistent_output

                # 3. Run Pipeline
                pipeline = ResumePipeline(config)

                # Hook up progress reporting
                def progress_callback(stage, percent, msg):
                    self.rabbitmq.publish_progress(
                        job.id,
                        getattr(
                            PipelineStage, stage.upper(), PipelineStage.GENERATING_DRAFT
                        ),
                        percent,
                        msg,
                    )

                if hasattr(pipeline, "set_progress_callback"):
                    pipeline.set_progress_callback(progress_callback)

                # Execute
                structured_resume, raw_output, pdf_path = pipeline.run()

                # 4. Update DB on Success
                job.status = "completed"
                job.completed_at = datetime.now(UTC)
                job.final_score = self._extract_score(persistent_output)

                # Store paths relative to output root
                job.output_files = {
                    "pdf": str(pdf_path) if pdf_path else None,
                    "dir": str(persistent_output),
                }

                # Calculate duration
                if job.started_at:
                    job.processing_time_seconds = (
                        job.completed_at - job.started_at
                    ).total_seconds()

                db.commit()
                self.rabbitmq.publish_completion(
                    job.id, job.output_files, str(job.started_at)
                )

            except Exception as e:
                logger.error(f"Pipeline failed: {traceback.format_exc()}")
                job.status = "failed"
                job.error_message = str(e)
                db.commit()
                self.rabbitmq.publish_error(job.id, str(e), str(job.started_at))

            finally:
                db.close()

    def _extract_score(self, output_dir: Path) -> float:
        """Helper to try and read the score from the critic JSON output."""
        try:
            critique_path = output_dir / "checkpoint_critique.json"
            if critique_path.exists():
                data = json.load(open(critique_path))
                return float(data.get("score", 0.0))
        except:
            return 0.0
        return 0.0

    def start(self):
        self.rabbitmq.connect()
        self.rabbitmq.consume_jobs(self.process_job)

            return 0.0
        return 0.0

    def start(self):
        self.rabbitmq.connect()
        self.rabbitmq.consume_jobs(self.process_job)

if __name__ == "__main__":
    worker = DatabaseResumeWorker()
    worker.start()
