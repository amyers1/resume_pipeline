"""
Resume Pipeline Worker
Processes resume generation jobs from RabbitMQ queue
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pika

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "resume_queue")
JOBS_DIR = Path("jobs")
OUTPUT_DIR = Path("output")


def update_job_metadata(job_id: str, updates: dict) -> bool:
    """Update job metadata file"""
    metadata_path = JOBS_DIR / f"{job_id}_metadata.json"

    if not metadata_path.exists():
        logger.warning(f"Metadata file not found for job {job_id}")
        return False

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        metadata.update(updates)

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Updated metadata for job {job_id}: {updates}")
        return True
    except Exception as e:
        logger.error(f"Failed to update metadata for job {job_id}: {e}")
        return False


def extract_final_score(critique_file: Path) -> float:
    """Extract final score from critique.json file"""
    try:
        if not critique_file.exists():
            return None

        with open(critique_file, "r") as f:
            critique_data = json.load(f)

        # Try to find score in various possible locations
        if isinstance(critique_data, dict):
            # Look for common score field names
            for key in ["final_score", "score", "overall_score", "rating"]:
                if key in critique_data:
                    score = critique_data[key]
                    if isinstance(score, (int, float)):
                        return float(score)

            # Look for nested score
            if "analysis" in critique_data:
                analysis = critique_data["analysis"]
                if isinstance(analysis, dict) and "score" in analysis:
                    return float(analysis["score"])

        return None
    except Exception as e:
        logger.error(f"Failed to extract score from {critique_file}: {e}")
        return None


def process_resume_job(job_id: str) -> bool:
    """Process a single resume generation job"""
    start_time = time.time()

    logger.info(f"Starting job {job_id}")

    # Update metadata: job started
    update_job_metadata(job_id, {"status": "processing"})

    job_file = JOBS_DIR / f"{job_id}.json"

    if not job_file.exists():
        logger.error(f"Job file not found: {job_file}")
        update_job_metadata(
            job_id,
            {
                "status": "failed",
                "error": "Job file not found",
                "completed_at": datetime.utcnow().isoformat() + "Z",
            },
        )
        return False

    try:
        # Read job configuration
        with open(job_file, "r") as f:
            job_data = json.load(f)

        company = job_data.get("company", "Unknown")
        job_title = job_data.get("job_title", "Unknown")
        job_description = job_data.get("job_description", "")
        template = job_data.get("template", "awesome-cv")
        output_backend = job_data.get("output_backend", "weasyprint")
        career_profile = job_data.get("career_profile", "career_profile.json")

        logger.info(f"Job {job_id}: {company} - {job_title}")
        logger.info(f"Template: {template}, Backend: {output_backend}")

        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        run_timestamp = datetime.now().strftime("%H%M%S")
        output_path = OUTPUT_DIR / timestamp / f"run_{run_timestamp}"
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Output directory: {output_path}")

        # Save job description to output directory
        job_desc_file = output_path / "job_description.txt"
        with open(job_desc_file, "w") as f:
            f.write(f"Company: {company}\n")
            f.write(f"Job Title: {job_title}\n")
            f.write(f"\n{job_description}\n")

        # Run the resume generation pipeline
        # This is where you would call your actual resume generation code
        # For now, we'll simulate it

        logger.info(f"Running resume generation for job {job_id}")

        # Import and run your pipeline here
        # Example (adjust to your actual pipeline):
        try:
            from resume_pipeline import generate_resume

            result = generate_resume(
                career_profile=career_profile,
                job_description=job_description,
                company=company,
                job_title=job_title,
                output_dir=str(output_path),
                template=template,
                output_backend=output_backend,
            )

            logger.info(f"Resume generation completed for job {job_id}")

        except ImportError:
            # If pipeline not available, create dummy output files
            logger.warning("Resume pipeline not found, creating dummy files")

            # Create dummy files for testing
            dummy_pdf = output_path / f"resume_{company.replace(' ', '_')}.pdf"
            dummy_pdf.write_text("Dummy PDF content")

            dummy_tex = output_path / f"resume_{company.replace(' ', '_')}.tex"
            dummy_tex.write_text("Dummy LaTeX content")

            dummy_json = output_path / "job_analysis.json"
            with open(dummy_json, "w") as f:
                json.dump({"company": company, "title": job_title}, f)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Try to extract final score from critique.json
        critique_file = output_path / "critique.json"
        final_score = extract_final_score(critique_file)

        # Update metadata: job completed
        update_job_metadata(
            job_id,
            {
                "status": "completed",
                "output_dir": str(output_path.absolute()),
                "completed_at": datetime.utcnow().isoformat() + "Z",
                "processing_time_seconds": round(processing_time, 2),
                "final_score": final_score,
            },
        )

        logger.info(f"Job {job_id} completed successfully in {processing_time:.2f}s")
        return True

    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        logger.error(f"Job {job_id} failed: {error_msg}")

        # Update metadata: job failed
        update_job_metadata(
            job_id,
            {
                "status": "failed",
                "error": error_msg,
                "completed_at": datetime.utcnow().isoformat() + "Z",
                "processing_time_seconds": round(processing_time, 2),
            },
        )

        return False


def callback(ch, method, properties, body):
    """RabbitMQ callback for processing messages"""
    try:
        message = json.loads(body)
        job_id = message.get("job_id")

        if not job_id:
            logger.error("No job_id in message")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        logger.info(f"Received job: {job_id}")

        # Process the job
        success = process_resume_job(job_id)

        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

        if success:
            logger.info(f"Job {job_id} acknowledged")
        else:
            logger.warning(f"Job {job_id} failed but acknowledged")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Acknowledge even on error to prevent reprocessing
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    """Main worker loop"""
    logger.info("Resume Pipeline Worker starting...")
    logger.info(f"RabbitMQ Host: {RABBITMQ_HOST}")
    logger.info(f"RabbitMQ Queue: {RABBITMQ_QUEUE}")

    # Ensure directories exist
    JOBS_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    while True:
        try:
            # Connect to RabbitMQ
            logger.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST, heartbeat=600, blocked_connection_timeout=300
                )
            )
            channel = connection.channel()

            # Declare queue
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)

            # Set QoS to process one message at a time
            channel.basic_qos(prefetch_count=1)

            # Start consuming
            logger.info("Waiting for messages. To exit press CTRL+C")
            channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)

            channel.start_consuming()

        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
            break
        except Exception as e:
            logger.error(f"Connection error: {e}")
            logger.info("Reconnecting in 5 seconds...")
            time.sleep(5)

    logger.info("Worker shutting down")


if __name__ == "__main__":
    main()
