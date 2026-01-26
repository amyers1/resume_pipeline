import asyncio
import json
import logging
import os
import time
from enum import Enum

import aio_pika
import pika

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rabbitmq")

# Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")


class MessageType(str, Enum):
    JOB_CREATED = "JOB_CREATED"
    JOB_STARTED = "JOB_STARTED"
    JOB_PROGRESS = "JOB_PROGRESS"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"


class PipelineStage(str, Enum):
    INITIALIZATION = "INITIALIZATION"
    ANALYSIS = "ANALYSIS"
    GENERATING_DRAFT = "GENERATING_DRAFT"
    CRITIQUE = "CRITIQUE"
    REFINEMENT = "REFINEMENT"
    FORMATTING = "FORMATTING"
    COMPLETE = "COMPLETE"


class JobRequest:
    def __init__(
        self,
        job_id,
        job_json_path,
        career_profile_path,
        template="awesome-cv",
        output_backend="weasyprint",
        priority=5,
    ):
        self.job_id = job_id
        self.job_json_path = job_json_path
        self.career_profile_path = career_profile_path
        self.template = template
        self.output_backend = output_backend
        self.priority = priority

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(data):
        return JobRequest(**data)


class RabbitMQConfig:
    def __init__(self):
        self.host = RABBITMQ_HOST
        self.port = RABBITMQ_PORT
        self.user = RABBITMQ_USER
        self.password = RABBITMQ_PASS
        self.job_queue = "resume_jobs"
        self.status_queue = "resume_status"
        self.progress_queue = "resume_progress"


class AsyncRabbitMQClient:
    def __init__(self, config: RabbitMQConfig = None):
        self.config = config or RabbitMQConfig()
        self.connection = None
        self.channel = None

    async def connect(self):
        """Establishes an async connection to RabbitMQ with retry logic."""
        if self.connection and not self.connection.is_closed:
            return

        for i in range(5):
            try:
                self.connection = await aio_pika.connect_robust(
                    host=self.config.host,
                    port=self.config.port,
                    login=self.config.user,
                    password=self.config.password,
                    loop=asyncio.get_running_loop(),
                )
                self.channel = await self.connection.channel()

                # Declare queues
                await self.channel.declare_queue(self.config.job_queue, durable=True)
                await self.channel.declare_queue(self.config.status_queue, durable=True)
                await self.channel.declare_queue(
                    self.config.progress_queue, durable=True
                )

                logger.info(f"✅ Connected to RabbitMQ at {self.config.host}")
                return
            except Exception as e:
                logger.warning(f"⚠️ RabbitMQ connection attempt {i + 1} failed: {e}")
                await asyncio.sleep(5)

        raise Exception("❌ Could not connect to RabbitMQ")

    async def close(self):
        """Closes the connection."""
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    async def _publish(
        self,
        queue_name: str,
        payload: dict,
        delivery_mode: aio_pika.DeliveryMode = None,
    ):
        """Internal helper to publish messages."""
        if not self.channel:
            await self.connect()

        message = aio_pika.Message(
            body=json.dumps(payload).encode(), delivery_mode=delivery_mode
        )
        await self.channel.default_exchange.publish(message, routing_key=queue_name)

    async def publish_job_status(self, job_id: str, status: MessageType):
        """Publishes a status update (Started, Completed, Failed)."""
        payload = {"job_id": job_id, "type": status, "timestamp": time.time()}
        await self._publish(self.config.status_queue, payload)

    async def publish_job(self, job_request: JobRequest):
        """Publishes a new job request."""
        await self._publish(
            self.config.job_queue,
            job_request.to_dict(),
            aio_pika.DeliveryMode.PERSISTENT,
        )
        logger.info(f"📨 Published Job {job_request.job_id}")

    async def publish_progress(
        self, job_id: str, stage: str, percent: int, message: str
    ):
        """Publishes progress updates."""
        # Using a try/except block to ensure progress updates don't crash the worker
        try:
            if not self.channel:
                await self.connect()

            payload = {
                "job_id": job_id,
                "type": MessageType.JOB_PROGRESS,
                "stage": stage,
                "percent": percent,
                "message": message,
                "timestamp": time.time(),
            }
            await self._publish(self.config.progress_queue, payload)
        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")

    async def publish_completion(
        self, job_id: str, output_files: dict, started_at: str
    ):
        """Publishes job completion status."""
        payload = {
            "job_id": job_id,
            "type": MessageType.JOB_COMPLETED,
            "output_files": output_files,
            "started_at": started_at,
            "timestamp": time.time(),
        }
        await self._publish(self.config.status_queue, payload)

    async def publish_error(self, job_id: str, error_msg: str, started_at: str):
        """Publishes job error status."""
        payload = {
            "job_id": job_id,
            "type": MessageType.JOB_FAILED,
            "error": error_msg,
            "started_at": started_at,
            "timestamp": time.time(),
        }
        await self._publish(self.config.status_queue, payload)

    async def consume_jobs(self, callback: Callable[[JobRequest], Awaitable[None]]):
        """
        Consumes jobs from the queue asynchronously.

        Args:
            callback: An async function that takes a JobRequest as input.
        """
        if not self.channel:
            await self.connect()

        # Set QoS to process 1 job at a time per worker instance
        await self.channel.set_qos(prefetch_count=1)

        queue = await self.channel.declare_queue(self.config.job_queue, durable=True)

        logger.info("👀 Worker waiting for jobs...")

        # Continuous consumption loop
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode())
                        request = JobRequest.from_dict(data)
                        logger.info(f"📥 Received Job: {request.job_id}")
                        await callback(request)
                    except Exception as e:
                        logger.error(f"❌ Error processing job: {e}")
                        # message.process() automatically nacks on exception
                        # If you want to prevent requeue loops for bad data, handle it here.


# Helper used by API
async def publish_job_request(
    job_id, job_json_path, career_profile_path, template, output_backend, priority
):
    """
    Async helper to publish a single job request.
    Creates a temporary connection and closes it after publishing.
    """
    client = AsyncRabbitMQClient()
    try:
        await client.connect()
        req = JobRequest(
            job_id,
            job_json_path,
            career_profile_path,
            template,
            output_backend,
            priority,
        )
        await client.publish_job(req)
    finally:
        await client.close()


# class RabbitMQClient:
#     def __init__(self, config: RabbitMQConfig = None):
#         self.config = config or RabbitMQConfig()
#         self.connection = None
#         self.channel = None

#     def connect(self):
#         credentials = pika.PlainCredentials(self.config.user, self.config.password)
#         parameters = pika.ConnectionParameters(
#             host=self.config.host,
#             port=self.config.port,
#             credentials=credentials,
#             heartbeat=600,
#             blocked_connection_timeout=300,
#         )

#         # Retry logic for startup
#         for i in range(5):
#             try:
#                 self.connection = pika.BlockingConnection(parameters)
#                 self.channel = self.connection.channel()
#                 self.channel.queue_declare(queue=self.config.job_queue, durable=True)
#                 self.channel.queue_declare(queue=self.config.status_queue, durable=True)
#                 self.channel.queue_declare(
#                     queue=self.config.progress_queue, durable=True
#                 )
#                 logger.info(f"✅ Connected to RabbitMQ at {self.config.host}")
#                 return
#             except Exception as e:
#                 logger.warning(f"⚠️ RabbitMQ connection attempt {i + 1} failed: {e}")
#                 time.sleep(5)

#         raise Exception("❌ Could not connect to RabbitMQ")

#     # --- THE METHOD CAUSING YOUR ERROR ---
#     def publish_job_status(self, job_id: str, status: MessageType):
#         """Publishes a status update (Started, Completed, Failed)."""
#         if not self.channel:
#             self.connect()

#         payload = {"job_id": job_id, "type": status, "timestamp": time.time()}
#         self.channel.basic_publish(
#             exchange="", routing_key=self.config.status_queue, body=json.dumps(payload)
#         )

#     # -------------------------------------

#     def publish_job(self, job_request: JobRequest):
#         if not self.channel:
#             self.connect()
#         self.channel.basic_publish(
#             exchange="",
#             routing_key=self.config.job_queue,
#             body=json.dumps(job_request.to_dict()),
#             properties=pika.BasicProperties(delivery_mode=2),
#         )
#         logger.info(f"📨 Published Job {job_request.job_id}")

#     def publish_progress(self, job_id: str, stage: str, percent: int, message: str):
#         if not self.channel:
#             try:
#                 self.connect()
#             except:
#                 return

#         payload = {
#             "job_id": job_id,
#             "type": MessageType.JOB_PROGRESS,
#             "stage": stage,
#             "percent": percent,
#             "message": message,
#             "timestamp": time.time(),
#         }
#         self.channel.basic_publish(
#             exchange="",
#             routing_key=self.config.progress_queue,
#             body=json.dumps(payload),
#         )

#     def publish_completion(self, job_id: str, output_files: dict, started_at: str):
#         if not self.channel:
#             self.connect()
#         payload = {
#             "job_id": job_id,
#             "type": MessageType.JOB_COMPLETED,
#             "output_files": output_files,
#             "started_at": started_at,
#             "timestamp": time.time(),
#         }
#         self.channel.basic_publish(
#             exchange="", routing_key=self.config.status_queue, body=json.dumps(payload)
#         )

#     def publish_error(self, job_id: str, error_msg: str, started_at: str):
#         if not self.channel:
#             self.connect()
#         payload = {
#             "job_id": job_id,
#             "type": MessageType.JOB_FAILED,
#             "error": error_msg,
#             "started_at": started_at,
#             "timestamp": time.time(),
#         }
#         self.channel.basic_publish(
#             exchange="", routing_key=self.config.status_queue, body=json.dumps(payload)
#         )

#     def consume_jobs(self, callback):
#         if not self.channel:
#             self.connect()
#         self.channel.basic_qos(prefetch_count=1)

#         def on_message(ch, method, properties, body):
#             try:
#                 data = json.loads(body)
#                 request = JobRequest.from_dict(data)
#                 logger.info(f"📥 Received Job: {request.job_id}")
#                 callback(request)
#                 ch.basic_ack(delivery_tag=method.delivery_tag)
#             except Exception as e:
#                 logger.error(f"❌ Error processing job: {e}")
#                 # Don't requeue immediately to avoid crash loops, but don't drop silently either
#                 # Ideally dead-letter, but here we just NACK
#                 ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

#         self.channel.basic_consume(
#             queue=self.config.job_queue, on_message_callback=on_message
#         )
#         logger.info("👀 Worker waiting for jobs...")
#         self.channel.start_consuming()

# # Helper used by API
# def publish_job_request(
#     job_id, job_json_path, career_profile_path, template, output_backend, priority
# ):
#     client = RabbitMQClient()
#     req = JobRequest(
#         job_id, job_json_path, career_profile_path, template, output_backend, priority
#     )
#     client.publish_job(req)
