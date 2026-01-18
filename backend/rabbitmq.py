import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

import pika
from pika.exceptions import AMQPChannelError, AMQPConnectionError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in the resume pipeline."""

    JOB_REQUEST = "job_request"
    JOB_STARTED = "job_started"
    JOB_PROGRESS = "job_progress"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"


class PipelineStage(Enum):
    """Stages in the resume generation pipeline."""

    ANALYZING_JD = "analyzing_jd"
    MATCHING_ACHIEVEMENTS = "matching_achievements"
    GENERATING_DRAFT = "generating_draft"
    CRITIQUING = "critiquing"
    REFINING = "refining"
    GENERATING_OUTPUT = "generating_output"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"


@dataclass
class JobRequest:
    job_id: str
    template: str
    output_backend: str
    priority: int
    # Paths are now optional/ignored as we use DB,
    # but kept for compatibility if needed
    job_json_path: str = "DB"
    career_profile_path: str = "DB"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRequest":
        # Safe extraction of known fields
        return cls(
            job_id=data.get("job_id"),
            template=data.get("template", "awesome-cv"),
            output_backend=data.get("output_backend", "weasyprint"),
            priority=data.get("priority", 5),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class JobStatus:
    """Represents the status of a job."""

    job_id: str
    status: MessageType
    stage: Optional[PipelineStage] = None
    progress_percent: int = 0
    message: str = ""
    output_files: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.status:
            data["status"] = self.status.value
        if self.stage:
            data["stage"] = self.stage.value
        return data


class RabbitMQConfig:
    """Configuration for RabbitMQ connection."""

    def __init__(self):
        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.username = os.getenv("RABBITMQ_USERNAME", "guest")
        self.password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.vhost = os.getenv("RABBITMQ_VHOST", "/")

        # Queue names
        self.job_queue = os.getenv("RABBITMQ_JOB_QUEUE", "resume.jobs")
        self.status_queue = os.getenv("RABBITMQ_STATUS_QUEUE", "resume.status")
        self.progress_queue = os.getenv("RABBITMQ_PROGRESS_QUEUE", "resume.progress")
        self.error_queue = os.getenv("RABBITMQ_ERROR_QUEUE", "resume.errors")

        # Exchange configuration
        self.exchange_name = os.getenv("RABBITMQ_EXCHANGE", "resume.events")
        self.exchange_type = "topic"

        # Connection settings
        self.heartbeat = int(os.getenv("RABBITMQ_HEARTBEAT", "600"))
        self.connection_attempts = int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "3"))
        self.retry_delay = int(os.getenv("RABBITMQ_RETRY_DELAY", "5"))

    def get_connection_params(self) -> pika.ConnectionParameters:
        """Get pika connection parameters."""
        credentials = pika.PlainCredentials(self.username, self.password)
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=credentials,
            heartbeat=self.heartbeat,
            connection_attempts=self.connection_attempts,
            retry_delay=self.retry_delay,
        )


class RabbitMQClient:
    """RabbitMQ client for the resume pipeline."""

    def __init__(self, config: Optional[RabbitMQConfig] = None):
        self.config = config or RabbitMQConfig()
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._is_connected = False

    def connect(self) -> bool:
        """Establish connection to RabbitMQ."""
        try:
            logger.info(
                f"Connecting to RabbitMQ at {self.config.host}:{self.config.port}"
            )
            self.connection = pika.BlockingConnection(
                self.config.get_connection_params()
            )
            self.channel = self.connection.channel()

            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.config.exchange_name,
                exchange_type=self.config.exchange_type,
                durable=True,
            )

            # Declare queues
            self._declare_queues()

            self._is_connected = True
            logger.info("Successfully connected to RabbitMQ")
            return True

        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self._is_connected = False
            return False

    def _declare_queues(self):
        """Declare all required queues."""
        queues = [
            (self.config.job_queue, {"x-max-priority": 10}),
            (self.config.status_queue, {}),
            (self.config.progress_queue, {}),
            (self.config.error_queue, {"x-message-ttl": 86400000}),  # 24 hour TTL
        ]

        for queue_name, arguments in queues:
            self.channel.queue_declare(
                queue=queue_name, durable=True, arguments=arguments
            )

            # Bind to exchange
            routing_key = f"resume.{queue_name.split('.')[-1]}"
            self.channel.queue_bind(
                exchange=self.config.exchange_name,
                queue=queue_name,
                routing_key=routing_key,
            )

        logger.info("All queues declared and bound")

    def publish_message(
        self, routing_key: str, message: Dict[str, Any], priority: int = 0
    ) -> bool:
        """Publish a message to RabbitMQ."""
        if not self._is_connected:
            logger.warning("Not connected to RabbitMQ, attempting to connect...")
            if not self.connect():
                return False

        try:
            properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type="application/json",
                priority=priority,
                timestamp=int(time.time()),
            )

            self.channel.basic_publish(
                exchange=self.config.exchange_name,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=properties,
            )

            logger.debug(f"Published message to {routing_key}")
            return True

        except (AMQPConnectionError, AMQPChannelError) as e:
            logger.error(f"Failed to publish message: {e}")
            self._is_connected = False
            return False

    def publish_job_status(self, status: JobStatus) -> bool:
        """Publish job status update."""
        routing_key = f"resume.status.{status.status.value}"
        return self.publish_message(routing_key, status.to_dict())

    def publish_progress(
        self, job_id: str, stage: PipelineStage, percent: int, message: str = ""
    ) -> bool:
        """Publish progress update."""
        status = JobStatus(
            job_id=job_id,
            status=MessageType.JOB_PROGRESS,
            stage=stage,
            progress_percent=percent,
            message=message,
        )
        routing_key = "resume.progress"
        return self.publish_message(routing_key, status.to_dict())

    def publish_completion(
        self,
        job_id: str,
        output_files: Dict[str, str],
        started_at: str,
        message: str = "Job completed successfully",
    ) -> bool:
        """Publish job completion."""
        status = JobStatus(
            job_id=job_id,
            status=MessageType.JOB_COMPLETED,
            stage=PipelineStage.COMPLETED,
            progress_percent=100,
            message=message,
            output_files=output_files,
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
        )
        routing_key = "resume.status.job_completed"
        return self.publish_message(routing_key, status.to_dict())

    def publish_error(
        self,
        job_id: str,
        error: str,
        started_at: str,
        stage: Optional[PipelineStage] = None,
    ) -> bool:
        """Publish job failure."""
        status = JobStatus(
            job_id=job_id,
            status=MessageType.JOB_FAILED,
            stage=stage,
            error=error,
            message=f"Job failed: {error}",
            started_at=started_at,
            completed_at=datetime.utcnow().isoformat(),
        )
        routing_key = "resume.status.job_failed"
        return self.publish_message(routing_key, status.to_dict())

    def consume_jobs(self, callback: Callable[[JobRequest], None]):
        """
        Start consuming job requests from the queue.

        Args:
            callback: Function to call when a job request is received.
                     Should accept a JobRequest and return None.
        """
        if not self._is_connected:
            if not self.connect():
                raise ConnectionError("Failed to connect to RabbitMQ")

        def on_message(channel, method, properties, body):
            """Handle incoming message."""
            try:
                data = json.loads(body)
                job_request = JobRequest.from_dict(data)

                logger.info(f"Received job request: {job_request.job_id}")

                # Acknowledge message
                channel.basic_ack(delivery_tag=method.delivery_tag)

                # Process job
                callback(job_request)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message: {e}")
                # Reject and requeue malformed messages
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Reject but don't requeue to avoid infinite loops
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        # Set QoS to process one message at a time
        self.channel.basic_qos(prefetch_count=1)

        # Start consuming
        self.channel.basic_consume(
            queue=self.config.job_queue, on_message_callback=on_message
        )

        logger.info(f"Started consuming from {self.config.job_queue}")
        logger.info("Waiting for job requests. Press Ctrl+C to exit.")

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.channel.stop_consuming()

    def close(self):
        """Close the connection to RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            self._is_connected = False
            logger.info("Closed RabbitMQ connection")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def publish_job_request(
    job_id: str,
    job_json_path: str = "DB",
    career_profile_path: str = "DB",
    template: str = "awesome-cv",
    output_backend: str = "weasyprint",
    priority: int = 5,
    enable_uploads: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Publish a job request to RabbitMQ.

    Args:
        job_id: Unique identifier for the job
        job_json_path: Path to job JSON or 'DB' if using database
        career_profile_path: Path to profile JSON or 'DB'
        template: Resume template to use
        output_backend: 'weasyprint' or 'latex'
        priority: Job priority (1-10)
        enable_uploads: Whether to upload results to cloud storage
        metadata: Additional metadata

    Returns:
        The job_id
    """
    job_request = JobRequest(
        job_id=job_id,
        job_json_path=job_json_path,
        career_profile_path=career_profile_path,
        template=template,
        output_backend=output_backend,
        priority=priority,
    )

    with RabbitMQClient() as client:
        routing_key = "resume.jobs"
        client.publish_message(routing_key, job_request.to_dict(), priority=priority)

    return job_id
