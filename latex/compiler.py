"""LaTeX compilation with S3 storage."""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import structlog

from config import settings
from s3_manager import s3_manager

logger = structlog.get_logger()


class LaTeXCompiler:
    """Compiles LaTeX documents and stores results in S3."""

    def __init__(self):
        self.xelatex_path = shutil.which("xelatex")
        self.pdflatex_path = shutil.which("pdflatex")

        if not self.xelatex_path and not self.pdflatex_path:
            logger.error("No LaTeX compiler found!")

    def compile(
        self,
        tex_content: str,
        job_id: str,
        filename: str = "resume.tex",
        engine: str = "xelatex",
        create_backup: bool = True
    ) -> Dict:
        """
        Compile LaTeX to PDF and upload to S3.

        Returns compilation result with S3 paths.
        """
        log = logger.bind(job_id=job_id, engine=engine)
        log.info("Starting compilation")

        # Create temporary working directory
        work_dir = settings.temp_dir / job_id
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Write tex file
            tex_path = work_dir / filename
            tex_path.write_text(tex_content, encoding="utf-8")

            # Create backup in S3 if requested
            if create_backup:
                self._backup_to_s3(job_id, tex_content, filename)

            # Copy template files
            self._copy_template_files(work_dir)

            # Choose compiler
            if engine == "xelatex":
                compiler_path = self.xelatex_path
            else:
                compiler_path = self.pdflatex_path

            if not compiler_path:
                raise Exception(f"Compiler {engine} not available")

            # Compile
            errors = []
            warnings = []
            log_output = ""

            for pass_num in range(1, settings.latex_compile_passes + 1):
                log.info(f"Compilation pass {pass_num}")

                result = subprocess.run(
                    [compiler_path, "-interaction=nonstopmode", "-halt-on-error", filename],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=settings.latex_timeout
                )

                log_output += result.stdout

                if result.returncode != 0:
                    errors = self._parse_errors(result.stdout)
                    return {
                        "success": False,
                        "job_id": job_id,
                        "errors": errors,
                        "warnings": [],
                        "log": log_output,
                        "compiled_at": datetime.utcnow().isoformat()
                    }

            # Check for PDF
            pdf_path = tex_path.with_suffix(".pdf")
            if not pdf_path.exists():
                raise Exception("PDF not created")

            # Upload PDF to S3
            s3_pdf_key = f"{job_id}/{pdf_path.name}"
            if not s3_manager.upload_file(pdf_path, s3_pdf_key):
                raise Exception("Failed to upload PDF to S3")

            # Upload tex file to S3
            s3_tex_key = f"{job_id}/{filename}"
            s3_manager.upload_file(tex_path, s3_tex_key)

            # Upload log if configured
            if settings.latex_keep_aux_files:
                log_path = tex_path.with_suffix(".log")
                if log_path.exists():
                    s3_manager.upload_file(log_path, f"{job_id}/{log_path.name}")

            warnings = self._parse_warnings(log_output)

            log.info("Compilation successful", pdf_key=s3_pdf_key)

            return {
                "success": True,
                "job_id": job_id,
                "pdf_s3_key": s3_pdf_key,
                "tex_s3_key": s3_tex_key,
                "errors": [],
                "warnings": warnings,
                "log": log_output,
                "compiled_at": datetime.utcnow().isoformat()
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "job_id": job_id,
                "errors": [{"line": None, "message": "Compilation timeout"}],
                "warnings": [],
                "log": log_output,
                "compiled_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            log.error(f"Compilation failed: {e}")
            return {
                "success": False,
                "job_id": job_id,
                "errors": [{"line": None, "message": str(e)}],
                "warnings": [],
                "log": log_output,
                "compiled_at": datetime.utcnow().isoformat()
            }

        finally:
            # Cleanup temporary files
            if work_dir.exists():
                shutil.rmtree(work_dir)

    def _backup_to_s3(self, job_id: str, content: str, filename: str):
        """Create versioned backup in S3."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_key = f"{job_id}/backups/{Path(filename).stem}_backup_{timestamp}.tex"

        s3_manager.upload_bytes(
            content.encode("utf-8"),
            backup_key,
            content_type="text/x-tex"
        )

        # Cleanup old backups
        self._cleanup_old_backups(job_id)

    def _cleanup_old_backups(self, job_id: str):
        """Remove old backups exceeding limit."""
        versions = s3_manager.list_versions(job_id)

        if len(versions) > settings.max_versions_per_job:
            for old_version in versions[settings.max_versions_per_job:]:
                try:
                    s3_manager.client.remove_object(
                        s3_manager.bucket,
                        old_version["s3_key"]
                    )
                    logger.info(f"Removed old backup: {old_version['filename']}")
                except Exception as e:
                    logger.error(f"Failed to remove backup: {e}")

    def _copy_template_files(self, work_dir: Path):
        """Copy template files to working directory."""
        if not settings.templates_dir.exists():
            return

        for template_file in settings.templates_dir.rglob("*.cls"):
            dest = work_dir / template_file.name
            if not dest.exists():
                shutil.copy2(template_file, dest)

        for template_file in settings.templates_dir.rglob("*.sty"):
            dest = work_dir / template_file.name
            if not dest.exists():
                shutil.copy2(template_file, dest)

    def _parse_errors(self, log: str) -> List[Dict]:
        """Parse LaTeX errors from log."""
        errors = []
        lines = log.split('\n')

        for i, line in enumerate(lines):
            if line.startswith('!'):
                error_msg = line[1:].strip()
                line_num = None

                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if 'l.' in next_line:
                        try:
                            line_num = int(next_line.split('l.')[1].split()[0])
                        except (IndexError, ValueError):
                            pass

                errors.append({
                    "line": line_num,
                    "message": error_msg,
                    "type": "error"
                })

        return errors

    def _parse_warnings(self, log: str) -> List[Dict]:
        """Parse LaTeX warnings."""
        warnings = []

        for line in log.split('\n'):
            if 'Warning:' in line:
                warnings.append({
                    "line": None,
                    "message": line.strip(),
                    "type": "warning"
                })

        return warnings[:10]
