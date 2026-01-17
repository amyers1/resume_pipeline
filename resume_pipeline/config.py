"""
Configuration management for resume pipeline.
"""

import hashlib
import json
import os
from datetime import datetime
from imaplib import Commands
from pathlib import Path
from typing import Optional

import pytz
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class PipelineConfig(BaseModel):
    """Configuration for resume generation pipeline."""

    company: str = Field(default="Company Name")
    job_title: str = Field(default="Job Title")
    base_file_name: str = Field(default="resume")
    top_k_heuristic: int = Field(default=20)
    top_k_final: int = Field(default=12)
    critique_threshold: float = Field(default=0.80)
    max_critique_loops: int = Field(default=2)
    escalate_on_second_pass: bool = Field(default=False)

    # API Keys
    openai_api_key: Optional[str] = Field(default=None)
    google_api_key: Optional[str] = Field(default=None)

    # LLM Models
    base_model: str = Field(default="gpt-5-mini")
    strong_model: str = Field(default="gpt-5-mini")

    # Input paths
    job_json_path: Path
    career_profile_path: Path = Field(default=Path("career_profile.json"))

    # Output configuration
    output_dir: Path = Field(default=Path("./output"))
    output_backend: str = Field(default="weasyprint")  # 'weasyprint' or 'latex'

    # LaTeX configuration (used if output_backend='latex')
    latex_template: str = Field(default="awesome-cv")
    compile_pdf: bool = Field(default=False)

    # HTML/CSS configuration (used if output_backend='weasyprint')
    template_name: str = Field(default="resume.html.j2")
    css_file: str = Field(default="resume.css")

    # Caching
    use_cache: bool = Field(default=True)

    # Redis cache configuration
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    redis_cache_ttl_days: int = Field(default=30)

    # Legacy file-based cache (deprecated)
    cache_dir: Path = Field(default=Path("./output/.cache"))

    # Timezone
    timezone_str: str = Field(default="America/New_York")

    # Cloud uploads
    enable_minio: bool = Field(default=False)
    minio_endpoint: str = Field(default="")
    minio_access_key: str = Field(default="")
    minio_secret_key: str = Field(default="")
    minio_bucket: str = Field(default="resumes")

    enable_nextcloud: bool = Field(default=False)
    nextcloud_endpoint: str = Field(default="")
    nextcloud_user: str = Field(default="")
    nextcloud_password: str = Field(default="")

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_env(
        cls,
        company: str,
        job_title: str,
        base_file_name: str,
        job_json_path: Optional[str] = None,
    ) -> "PipelineConfig":
        """Create configuration from environment variables."""
        company = company
        job_title = job_title
        base_file_name = base_file_name

        # Get job path from parameter or environment
        if job_json_path:
            job_path = Path(job_json_path)
        else:
            job_path_str = os.getenv("JOB_JSON_PATH")
            if not job_path_str:
                raise ValueError("JOB_JSON_PATH must be set")
            job_path = Path(job_path_str)

        return cls(
            # Pipeline Configuration
            top_k_heuristic=int(os.getenv("TOP_K_HEURISTIC", "20")),
            top_k_final=int(os.getenv("TOP_K_FINAL", "12")),
            critique_threshold=float(os.getenv("CRITIQUE_THRESHOLD", "0.80")),
            max_critique_loops=int(os.getenv("MAX_CRITIQUE_LOOPS", "2")),
            escalate_on_second_pass=(
                os.getenv("ESCALATE_ON_SECOND_PASS", "false").lower() == "true"
            ),
            # API Keys
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            # Models
            base_model=os.getenv("MODEL", "gpt-5-mini"),
            strong_model=os.getenv("STRONG_MODEL", "gpt-5-mini"),
            # Paths
            job_json_path=job_path,
            career_profile_path=Path(
                os.getenv("CAREER_PROFILE_PATH", "career_profile.json")
            ),
            output_dir=Path(os.getenv("OUTPUT_DIR", "./output")),
            # Output backend
            output_backend=os.getenv("OUTPUT_BACKEND", "weasyprint"),
            latex_template=os.getenv("LATEX_TEMPLATE", "modern-deedy"),
            compile_pdf=os.getenv("COMPILE_PDF", "false").lower() == "true",
            template_name=os.getenv("TEMPLATE_NAME", "resume.html.j2"),
            css_file=os.getenv("CSS_FILE", "resume.css"),
            # Caching
            use_cache=os.getenv("USE_CACHE", "true").lower() == "true",
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD") or None,
            redis_cache_ttl_days=int(os.getenv("REDIS_CACHE_TTL_DAYS", "30")),
            cache_dir=Path(os.getenv("CACHE_DIR", "./output/.cache")),
            # Timezone
            timezone_str=os.getenv("TIMEZONE", "America/New_York"),
            # Cloud uploads
            enable_minio=os.getenv("ENABLE_MINIO", "false").lower() == "true",
            minio_endpoint=os.getenv("MINIO_ENDPOINT", ""),
            minio_access_key=os.getenv("MINIO_ACCESS_KEY", ""),
            minio_secret_key=os.getenv("MINIO_SECRET_KEY", ""),
            minio_bucket=os.getenv("MINIO_BUCKET", "resumes"),
            enable_nextcloud=os.getenv("ENABLE_NEXTCLOUD", "false").lower() == "true",
            nextcloud_endpoint=os.getenv("NEXTCLOUD_URL", ""),
            nextcloud_user=os.getenv("NEXTCLOUD_USERNAME", ""),
            nextcloud_password=os.getenv("NEXTCLOUD_PASSWORD", ""),
        )

    @property
    def timezone(self) -> pytz.timezone:
        """Get timezone object."""
        return pytz.timezone(self.timezone_str)

    @property
    def now(self) -> datetime:
        """Get current time in configured timezone."""
        return datetime.now(self.timezone)

    @property
    def current_year(self) -> str:
        """Get date stamp for output directory (YYYYMMDD)."""
        return self.now.strftime("%Y")

    @property
    def date_stamp(self) -> str:
        """Get date stamp for output directory (YYYYMMDD)."""
        return self.now.strftime("%Y%m%d")

    @property
    def time_stamp(self) -> str:
        """Get time stamp for output directory (HHMMSS)."""
        return self.now.strftime("%H%M%S")

    @property
    def full_timestamp(self) -> str:
        """Get time stamp for output directory (HHMMSS)."""
        return f"{self.date_stamp}_{self.time_stamp}"

    def get_checkpoint_filename(self, name: str) -> str:
        """Get standardized checkpoint filename."""
        return f"checkpoint_{name}.json"

    @property
    def template_files_dir(self) -> Path:
        """Get templates directory path."""
        return Path(__file__).parent.parent / "templates"

    def get_output_dir(self) -> Path:
        """
        Create and return output directory with date/time structure.

        Structure: output/YYYYMMDD/run_HHMMSS/
        Also creates a 'latest' symlink to the most recent run.
        """
        # Create date-based directory
        date_dir = self.output_dir / self.date_stamp
        date_dir.mkdir(parents=True, exist_ok=True)

        # Create run directory with timestamp
        run_dir = date_dir / f"run_{self.time_stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create/update 'latest' symlink
        latest_link = date_dir / "latest"
        if latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(run_dir.name)

        return run_dir

    def get_output_filename(self, ext: str) -> str:
        """Get standardized output filename."""
        return f"{self.base_file_name}.{ext}"

    def print_config_summary(self):
        """Print configuration summary for debugging."""
        print("\n" + "=" * 80)
        print("PIPELINE CONFIGURATION")
        print("=" * 80)
        print(f"Job: {self.job_json_path}")
        print(f"Models: {self.base_model} / {self.strong_model}")
        print(f"Output Backend: {self.output_backend}")

        if self.output_backend == "latex":
            print(f"LaTeX Template: {self.latex_template}")
            print(f"Compile PDF: {self.compile_pdf}")
        else:
            print(f"HTML Template: {self.template_name}")
            print(f"CSS File: {self.css_file}")

        print(f"Caching: {'Enabled' if self.use_cache else 'Disabled'}")

        if self.use_cache:
            print(
                f"Redis Cache: {self.redis_host}:{self.redis_port} (DB {self.redis_db})"
            )
            print(f"Cache TTL: {self.redis_cache_ttl_days} days")

        print(f"Output Directory: {self.output_dir}")

        if self.enable_minio:
            print(f"MinIO Upload: Enabled → {self.minio_bucket}")
        if self.enable_nextcloud:
            print(f"Nextcloud Upload: Enabled → {self.nextcloud_endpoint}")

        print("=" * 80 + "\n")

    @staticmethod
    def compute_hash(data) -> str:
        """Compute SHA256 hash of data for cache keys."""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
