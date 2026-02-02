"""
LaTeX file versioning and backup management.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import structlog

from config import settings

logger = structlog.get_logger()


class VersionManager:
    """Manages LaTeX file versions and backups."""

    def __init__(self):
        self.backups_dir = settings.backups_dir

    def create_backup(self, job_id: str, content: str, filename: str = "resume.tex") -> str:
        """
        Create a backup of LaTeX content.

        Args:
            job_id: Job identifier
            content: LaTeX content to backup
            filename: Base filename

        Returns:
            Backup filename
        """
        log = logger.bind(job_id=job_id)

        # Create job backup directory
        job_backup_dir = self.backups_dir / job_id
        job_backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp-based filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{Path(filename).stem}_backup_{timestamp}.tex"
        backup_path = job_backup_dir / backup_filename

        # Write backup
        backup_path.write_text(content, encoding="utf-8")

        log.info("Created backup", backup_file=backup_filename)

        # Cleanup old backups
        self._cleanup_old_backups(job_id)

        return backup_filename

    def list_backups(self, job_id: str) -> List[dict]:
        """
        List all backups for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of backup metadata
        """
        job_backup_dir = self.backups_dir / job_id

        if not job_backup_dir.exists():
            return []

        backups = []
        for backup_file in sorted(job_backup_dir.glob("*.tex"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size_bytes": stat.st_size,
                "version_id": backup_file.stem
            })

        return backups

    def get_backup(self, job_id: str, version_id: str) -> Optional[str]:
        """
        Retrieve backup content.

        Args:
            job_id: Job identifier
            version_id: Version identifier (filename stem)

        Returns:
            Backup content or None
        """
        job_backup_dir = self.backups_dir / job_id

        # Find backup file
        for backup_file in job_backup_dir.glob(f"{version_id}*.tex"):
            return backup_file.read_text(encoding="utf-8")

        return None

    def _cleanup_old_backups(self, job_id: str):
        """Remove old backups exceeding max limit."""
        job_backup_dir = self.backups_dir / job_id

        backups = sorted(
            job_backup_dir.glob("*.tex"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # Remove oldest backups beyond limit
        for old_backup in backups[settings.max_versions_per_job:]:
            old_backup.unlink()
            logger.info("Removed old backup", backup=old_backup.name, job_id=job_id)
