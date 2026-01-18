#!/usr/bin/env python3
"""
Resume Job Monitor

Monitor resume generation jobs from RabbitMQ status queue.

Usage:
    python monitor_jobs.py                    # Monitor all jobs
    python monitor_jobs.py <job_id>           # Monitor specific job
    python monitor_jobs.py --continuous       # Continuous monitoring
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional

from resume_pipeline_rabbitmq import RabbitMQClient, RabbitMQConfig


class JobMonitor:
    """Monitor job status from RabbitMQ."""

    def __init__(self, job_id: Optional[str] = None):
        self.job_id = job_id
        self.config = RabbitMQConfig()
        self.jobs_seen = set()

    def start_monitoring(self, continuous: bool = False):
        """Start monitoring jobs."""
        with RabbitMQClient(self.config) as client:

            def on_status_message(channel, method, properties, body):
                """Handle status message."""
                try:
                    status = json.loads(body)

                    # Filter by job_id if specified
                    if self.job_id and status.get('job_id') != self.job_id:
                        channel.basic_ack(delivery_tag=method.delivery_tag)
                        return

                    self._display_status(status)

                    # Track jobs seen
                    self.jobs_seen.add(status.get('job_id'))

                    # Acknowledge message
                    channel.basic_ack(delivery_tag=method.delivery_tag)

                    # If monitoring single job and it's completed/failed, stop
                    if (self.job_id and
                        status.get('status') in ['job_completed', 'job_failed'] and
                        not continuous):
                        channel.stop_consuming()

                except json.JSONDecodeError as e:
                    print(f"Error parsing message: {e}")
                    channel.basic_ack(delivery_tag=method.delivery_tag)

            # Consume from both status and progress queues
            client.channel.basic_consume(
                queue=self.config.status_queue,
                on_message_callback=on_status_message
            )

            client.channel.basic_consume(
                queue=self.config.progress_queue,
                on_message_callback=on_status_message
            )

            print("Monitoring job status...")
            if self.job_id:
                print(f"Filtering for job: {self.job_id}")
            print("Press Ctrl+C to exit\n")

            try:
                client.channel.start_consuming()
            except KeyboardInterrupt:
                print("\nMonitoring stopped")
                client.channel.stop_consuming()

    def _display_status(self, status: dict):
        """Display job status in a formatted way."""
        job_id = status.get('job_id', 'unknown')
        status_type = status.get('status', 'unknown')
        message = status.get('message', '')
        stage = status.get('stage', '')
        progress = status.get('progress_percent', 0)
        error = status.get('error', '')

        # Format timestamp
        now = datetime.now().strftime('%H:%M:%S')

        # Color codes
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        RESET = '\033[0m'

        # Choose color based on status
        color = BLUE
        if status_type == 'job_completed':
            color = GREEN
        elif status_type == 'job_failed':
            color = RED
        elif status_type == 'job_progress':
            color = YELLOW

        # Build output
        output = f"[{now}] {color}{job_id}{RESET}"

        if status_type == 'job_started':
            output += f" - Started: {message}"

        elif status_type == 'job_progress':
            progress_bar = self._create_progress_bar(progress)
            output += f" - {progress_bar} {progress}%"
            if stage:
                output += f" - {stage.replace('_', ' ').title()}"
            if message:
                output += f" - {message}"

        elif status_type == 'job_completed':
            output += f" - ✓ Completed: {message}"
            output_files = status.get('output_files', {})
            if output_files:
                output += f"\n  Output directory: {output_files.get('output_dir', 'N/A')}"

        elif status_type == 'job_failed':
            output += f" - ✗ Failed: {error or message}"

        print(output)

    def _create_progress_bar(self, percent: int, width: int = 20) -> str:
        """Create a visual progress bar."""
        filled = int(width * percent / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}]"


def main():
    parser = argparse.ArgumentParser(
        description='Monitor resume generation jobs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'job_id',
        nargs='?',
        help='Specific job ID to monitor (optional)'
    )

    parser.add_argument(
        '-c', '--continuous',
        action='store_true',
        help='Continue monitoring after job completion'
    )

    args = parser.parse_args()

    monitor = JobMonitor(job_id=args.job_id)

    try:
        monitor.start_monitoring(continuous=args.continuous)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
