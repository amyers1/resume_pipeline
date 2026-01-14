#!/usr/bin/env python3
"""
Resume Job Producer

Submit resume generation jobs to RabbitMQ queue.

Usage:
    python submit_job.py jobs/my_job.json
    python submit_job.py jobs/my_job.json --template awesome-cv --priority 5
    python submit_job.py --help
"""

import argparse
import sys
from pathlib import Path

from resume_pipeline_rabbitmq import publish_job_request


def main():
    parser = argparse.ArgumentParser(
        description='Submit resume generation job to RabbitMQ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic job submission
  python submit_job.py jobs/dcs_position.json

  # With custom template
  python submit_job.py jobs/job.json --template awesome-cv

  # With high priority
  python submit_job.py jobs/urgent_job.json --priority 10

  # With different career profile
  python submit_job.py jobs/job.json --profile career_profile_v2.json

  # Batch submission
  for job in jobs/*.json; do
    python submit_job.py "$job"
  done
        """
    )

    parser.add_argument(
        'job_json',
        help='Path to job description JSON file'
    )

    parser.add_argument(
        '--profile',
        default='career_profile.json',
        help='Path to career profile JSON (default: career_profile.json)'
    )

    parser.add_argument(
        '--template',
        default='modern-deedy',
        choices=['modern-deedy', 'awesome-cv'],
        help='LaTeX template to use (default: modern-deedy)'
    )

    parser.add_argument(
        '--backend',
        default='weasyprint',
        choices=['weasyprint', 'latex'],
        help='Output backend (default: weasyprint)'
    )

    parser.add_argument(
        '--priority',
        type=int,
        default=0,
        help='Job priority (0-10, higher = more urgent, default: 0)'
    )

    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='Disable cloud uploads for this job'
    )

    args = parser.parse_args()

    # Validate job file exists
    job_path = Path(args.job_json)
    if not job_path.exists():
        print(f"Error: Job file not found: {args.job_json}", file=sys.stderr)
        sys.exit(1)

    # Validate career profile exists
    profile_path = Path(args.profile)
    if not profile_path.exists():
        print(f"Error: Career profile not found: {args.profile}", file=sys.stderr)
        sys.exit(1)

    # Validate priority range
    if not 0 <= args.priority <= 10:
        print("Error: Priority must be between 0 and 10", file=sys.stderr)
        sys.exit(1)

    # Submit job
    try:
        job_id = publish_job_request(
            job_json_path=str(job_path),
            career_profile_path=str(profile_path),
            template=args.template,
            output_backend=args.backend,
            priority=args.priority
        )

        print(f"✓ Job submitted successfully")
        print(f"  Job ID: {job_id}")
        print(f"  Job File: {args.job_json}")
        print(f"  Template: {args.template}")
        print(f"  Backend: {args.backend}")
        print(f"  Priority: {args.priority}")
        print()
        print("Track job status with:")
        print(f"  python monitor_jobs.py {job_id}")

    except Exception as e:
        print(f"Error submitting job: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
