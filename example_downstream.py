#!/usr/bin/env python3
"""
Example Downstream Service - Resume Archiver

This service demonstrates workflow chaining by:
1. Listening for completed resume jobs
2. Copying PDFs to a permanent archive
3. Creating metadata records
4. Publishing archive completion events

This shows how to chain the resume pipeline with other services.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import pika


class ResumeArchiver:
    """
    Example downstream service that archives completed resumes.

    This demonstrates:
    - Consuming from resume.status queue
    - Processing completed jobs
    - Publishing to next stage in workflow
    """

    def __init__(self, archive_dir: str = "./archive"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(exist_ok=True)

        # RabbitMQ connection
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=os.getenv('RABBITMQ_HOST', 'localhost'),
                port=int(os.getenv('RABBITMQ_PORT', '5672')),
                credentials=pika.PlainCredentials(
                    os.getenv('RABBITMQ_USERNAME', 'guest'),
                    os.getenv('RABBITMQ_PASSWORD', 'guest')
                )
            )
        )
        self.channel = self.connection.channel()

        # Declare queue for archive completion events
        self.channel.queue_declare(queue='resume.archived', durable=True)

    def process_completed_resume(self, channel, method, properties, body):
        """Process a completed resume job."""
        try:
            status = json.loads(body)

            # Only process completed jobs
            if status.get('status') != 'job_completed':
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            job_id = status['job_id']
            output_files = status.get('output_files', {})

            print(f"\n[Archiver] Processing job: {job_id}")

            # Archive the PDF
            pdf_path = output_files.get('pdf')
            if pdf_path and Path(pdf_path).exists():
                archived_path = self._archive_file(pdf_path, job_id)
                print(f"  ✓ Archived PDF: {archived_path}")

            # Archive the LaTeX source
            latex_path = output_files.get('latex')
            if latex_path and Path(latex_path).exists():
                archived_latex = self._archive_file(latex_path, job_id)
                print(f"  ✓ Archived LaTeX: {archived_latex}")

            # Create metadata record
            metadata = self._create_metadata(status)
            metadata_path = self.archive_dir / job_id / "metadata.json"
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps(metadata, indent=2))
            print(f"  ✓ Created metadata: {metadata_path}")

            # Publish archive completion event
            self._publish_archive_event(job_id, metadata)
            print(f"  ✓ Published archive event")

            # Acknowledge message
            channel.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"  ✗ Error processing job: {e}")
            # Reject but don't requeue
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _archive_file(self, source_path: str, job_id: str) -> Path:
        """Copy file to archive directory."""
        source = Path(source_path)
        archive_path = self.archive_dir / job_id / source.name
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, archive_path)
        return archive_path

    def _create_metadata(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata record for archived resume."""
        return {
            'job_id': status['job_id'],
            'archived_at': datetime.utcnow().isoformat(),
            'original_output': status.get('output_files', {}).get('output_dir'),
            'archive_location': str(self.archive_dir / status['job_id']),
            'processing_time': self._calculate_processing_time(status),
            'files': {
                'pdf': status.get('output_files', {}).get('pdf'),
                'latex': status.get('output_files', {}).get('latex'),
                'structured': status.get('output_files', {}).get('structured_resume')
            }
        }

    def _calculate_processing_time(self, status: Dict[str, Any]) -> float:
        """Calculate job processing time in seconds."""
        try:
            start = datetime.fromisoformat(status['started_at'])
            end = datetime.fromisoformat(status['completed_at'])
            return (end - start).total_seconds()
        except:
            return 0.0

    def _publish_archive_event(self, job_id: str, metadata: Dict[str, Any]):
        """Publish event that resume has been archived."""
        event = {
            'event_type': 'resume_archived',
            'job_id': job_id,
            'archived_at': metadata['archived_at'],
            'archive_location': metadata['archive_location'],
            'processing_time': metadata['processing_time']
        }

        self.channel.basic_publish(
            exchange='',
            routing_key='resume.archived',
            body=json.dumps(event),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type='application/json'
            )
        )

    def start(self):
        """Start consuming and archiving resumes."""
        print("Resume Archiver Started")
        print(f"Archive directory: {self.archive_dir}")
        print("Waiting for completed resumes...\n")

        # Consume from status queue
        self.channel.basic_consume(
            queue='resume.status',
            on_message_callback=self.process_completed_resume
        )

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print("\nArchiver stopped")
            self.channel.stop_consuming()
        finally:
            self.connection.close()


class EmailNotificationService:
    """
    Example service that sends email notifications when resumes complete.

    Another example of workflow chaining.
    """

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost')
        )
        self.channel = self.connection.channel()

    def send_notification(self, channel, method, properties, body):
        """Send email notification for completed resume."""
        status = json.loads(body)

        if status.get('status') == 'job_completed':
            job_id = status['job_id']
            output_dir = status['output_files']['output_dir']

            # In real implementation, send actual email
            print(f"\n[Email] Would send notification:")
            print(f"  To: user@example.com")
            print(f"  Subject: Resume Complete - {job_id}")
            print(f"  Body: Your resume is ready at {output_dir}\n")

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        """Start sending notifications."""
        print("Email Notification Service Started\n")

        self.channel.basic_consume(
            queue='resume.status',
            on_message_callback=self.send_notification
        )

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print("\nNotification service stopped")
            self.channel.stop_consuming()
        finally:
            self.connection.close()


class MetricsCollector:
    """
    Example service that collects metrics on resume generation.

    Demonstrates monitoring/analytics workflow.
    """

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost')
        )
        self.channel = self.connection.channel()

        self.metrics = {
            'total_jobs': 0,
            'completed': 0,
            'failed': 0,
            'avg_time': 0.0,
            'by_template': {}
        }

    def collect_metric(self, channel, method, properties, body):
        """Collect metrics from job events."""
        status = json.loads(body)
        job_status = status.get('status')

        if job_status == 'job_started':
            self.metrics['total_jobs'] += 1

        elif job_status == 'job_completed':
            self.metrics['completed'] += 1

            # Calculate processing time
            start = datetime.fromisoformat(status['started_at'])
            end = datetime.fromisoformat(status['completed_at'])
            duration = (end - start).total_seconds()

            # Update average
            n = self.metrics['completed']
            self.metrics['avg_time'] = (
                (self.metrics['avg_time'] * (n - 1) + duration) / n
            )

        elif job_status == 'job_failed':
            self.metrics['failed'] += 1

        # Print metrics every 5 jobs
        if self.metrics['total_jobs'] % 5 == 0:
            self._print_metrics()

        channel.basic_ack(delivery_tag=method.delivery_tag)

    def _print_metrics(self):
        """Print current metrics."""
        print("\n" + "="*50)
        print("Resume Generation Metrics")
        print("="*50)
        print(f"Total Jobs:     {self.metrics['total_jobs']}")
        print(f"Completed:      {self.metrics['completed']}")
        print(f"Failed:         {self.metrics['failed']}")
        print(f"Success Rate:   {self.metrics['completed'] / max(self.metrics['total_jobs'], 1) * 100:.1f}%")
        print(f"Avg Time:       {self.metrics['avg_time']:.1f}s")
        print("="*50 + "\n")

    def start(self):
        """Start collecting metrics."""
        print("Metrics Collector Started\n")

        # Consume from both status and progress queues
        self.channel.basic_consume(
            queue='resume.status',
            on_message_callback=self.collect_metric
        )

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print("\nMetrics collector stopped")
            self._print_metrics()
            self.channel.stop_consuming()
        finally:
            self.connection.close()


def main():
    """Run example downstream service."""
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python example_downstream.py archiver     # Start resume archiver")
        print("  python example_downstream.py email        # Start email notifications")
        print("  python example_downstream.py metrics      # Start metrics collector")
        sys.exit(1)

    service = sys.argv[1]

    if service == 'archiver':
        archiver = ResumeArchiver()
        archiver.start()

    elif service == 'email':
        notifier = EmailNotificationService()
        notifier.start()

    elif service == 'metrics':
        collector = MetricsCollector()
        collector.start()

    else:
        print(f"Unknown service: {service}")
        sys.exit(1)


if __name__ == '__main__':
    main()
