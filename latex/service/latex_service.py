"""
LaTeX Compilation Service - RabbitMQ Consumer

Consumes compilation requests from RabbitMQ, compiles LaTeX,
stores results in S3, and publishes progress/status updates.
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import aio_pika
import structlog
from compiler import LaTeXCompiler
from config import settings
from s3_manager import s3_manager

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

# Initialize compiler
compiler = LaTeXCompiler()

# Rate limiting
compilation_history = defaultdict(list)


class LatexService:
    """Async LaTeX compilation service."""

    def __init__(self):
        self.connection = None
        self.channel = None

    async def connect(self):
        """Connect to RabbitMQ."""
        logger.info("Connecting to RabbitMQ", host=settings.rabbitmq_host)

        self.connection = await aio_pika.connect_robust(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            login=settings.rabbitmq_user,
            password=settings.rabbitmq_pass,
        )

        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)

        logger.info("Connected to RabbitMQ")

    async def publish_progress(
        self, job_id: str, stage: str, percent: int, message: str
    ):
        """Publish progress update."""
        try:
            payload = {
                "job_id": job_id,
                "type": "LATEX_PROGRESS",
                "stage": stage,
                "percent": percent,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=settings.latex_progress_queue,
            )
        except Exception as e:
            logger.error(f"Failed to publish progress: {e}")

    async def publish_status(self, job_id: str, success: bool, result: dict):
        """Publish completion/failure status."""
        try:
            payload = {
                "job_id": job_id,
                "type": "LATEX_COMPLETED" if success else "LATEX_FAILED",
                "success": success,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

            await self.channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=settings.latex_status_queue,
            )
        except Exception as e:
            logger.error(f"Failed to publish status: {e}")

    def check_rate_limit(self, job_id: str) -> bool:
        """Check compilation rate limit."""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)

        compilation_history[job_id] = [
            ts for ts in compilation_history[job_id] if ts > cutoff
        ]

        if len(compilation_history[job_id]) >= settings.max_compilations_per_minute:
            return False

        compilation_history[job_id].append(now)
        return True

    async def process_compile_request(self, message: aio_pika.IncomingMessage):
        """Process compilation request from queue."""
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                job_id = data["job_id"]
                tex_content = data["content"]
                filename = data.get("filename", "resume.tex")
                engine = data.get("engine", "xelatex")
                create_backup = data.get("create_backup", True)

                log = logger.bind(job_id=job_id)
                log.info("Received compilation request")

                # Check rate limit
                if not self.check_rate_limit(job_id):
                    log.warning("Rate limit exceeded")
                    await self.publish_status(
                        job_id, False, {"error": "Rate limit exceeded"}
                    )
                    return

                # Validate size
                if len(tex_content) > settings.max_tex_file_size_kb * 1024:
                    log.warning("File too large")
                    await self.publish_status(
                        job_id, False, {"error": "File size exceeds limit"}
                    )
                    return

                # Publish progress
                await self.publish_progress(
                    job_id, "compiling", 10, "Starting compilation"
                )

                # Compile (blocking - run in executor)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    compiler.compile,
                    tex_content,
                    job_id,
                    filename,
                    engine,
                    create_backup,
                )

                # Publish result
                if result["success"]:
                    await self.publish_progress(
                        job_id, "completed", 100, "Compilation successful"
                    )
                    await self.publish_status(job_id, True, result)
                else:
                    await self.publish_status(job_id, False, result)

                log.info("Compilation finished", success=result["success"])

            except Exception as e:
                logger.error(f"Error processing request: {e}")
                try:
                    await self.publish_status(
                        data.get("job_id", "unknown"), False, {"error": str(e)}
                    )
                except:
                    pass

    async def start(self):
        """Start consuming compilation requests."""
        await self.connect()

        # Declare queues
        compile_queue = await self.channel.declare_queue(
            settings.latex_compile_queue, durable=True
        )

        await self.channel.declare_queue(settings.latex_progress_queue, durable=True)
        await self.channel.declare_queue(settings.latex_status_queue, durable=True)

        logger.info("Waiting for compilation requests...")

        # Start consuming
        await compile_queue.consume(self.process_compile_request)

        # Keep running
        await asyncio.Future()


async def start_consumer():
    """Main entry point for the RabbitMQ consumer."""
    logger.info("LaTeX Consumer Service starting...")
    logger.info(f"S3 enabled: {s3_manager.enabled}")
    logger.info(f"Templates: {settings.templates_dir}")

    service = LatexService()

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Service interrupted")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        if service.connection:
            await service.connection.close()
