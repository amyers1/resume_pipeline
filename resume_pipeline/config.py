"""
Configuration management for resume pipeline.
All settings now controlled via .env file.
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import pytz
from dotenv import load_dotenv


class PipelineConfig:
    """Central configuration for the resume pipeline - all settings from .env."""

    # Company abbreviations mapping
    COMPANY_ABBREV = {
        "Lockheed Martin": "lm",
        "Northrop Grumman": "ng",
        "Raytheon Technologies": "rtx",
        "General Dynamics": "gd",
        "Boeing": "boeing",
        "BAE Systems": "bae",
        "L3Harris": "l3harris",
        "Leidos": "leidos",
        "CACI": "caci",
        "Booz Allen Hamilton": "bah",
        "DCS Corporation": "dcs",
    }

    def __init__(self):
        """Initialize configuration from environment variables."""
        load_dotenv()

        # API Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

        # Model configuration
        self.base_model = os.getenv("MODEL", "gpt-4o-mini")
        self.strong_model = os.getenv("STRONG_MODEL", "gpt-4o-mini")

        # Validate API keys based on models
        if "gemini" in self.base_model or "gemini" in self.strong_model:
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")

        if "gpt" in self.base_model or "gpt" in self.strong_model:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")

        # Input/Output paths
        self.job_json_path = Path(os.getenv("JOB_JSON_PATH", "jobs/example_job.json"))
        self.career_profile_path = Path(
            os.getenv("CAREER_PROFILE_PATH", "career_profile.json")
        )
        output_dir = os.getenv("OUTPUT_DIR", "./output")

        # Validate required input files exist
        if not self.job_json_path.exists():
            raise FileNotFoundError(
                f"Job JSON file not found: {self.job_json_path}\n"
                f"Set JOB_JSON_PATH in .env to point to your job description file"
            )
        if not self.career_profile_path.exists():
            raise FileNotFoundError(
                f"Career profile not found: {self.career_profile_path}\n"
                f"Set CAREER_PROFILE_PATH in .env to point to your career profile"
            )

        # Timestamp for directory organization
        timezone = os.getenv("TIMEZONE", "America/New_York")
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        self.date_stamp = now.strftime("%Y%m%d")
        self.time_stamp = now.strftime("%H%M%S")
        self.full_timestamp = now.strftime("%Y%m%d_%H%M%S")

        # Load job JSON to get company and title
        job_json = json.loads(self.job_json_path.read_text(encoding="utf-8"))
        job_details = job_json.get("job_details", {})
        self.company = job_details.get("company", "Unknown_Company")
        self.job_title = job_details.get("job_title", "Unknown_Position")

        # Output directory setup
        self.base_output = Path(output_dir)
        self.output_dir = self.get_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cache directory (shared across dates)
        self.cache_dir = self.base_output / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.use_cache = os.getenv("USE_CACHE", "true").lower() == "true"

        # Template configuration
        self.latex_template = os.getenv("LATEX_TEMPLATE", "modern-deedy").lower()
        if self.latex_template not in ["modern-deedy", "awesome-cv"]:
            raise ValueError(
                f"Unknown template: {self.latex_template}. "
                "Use 'modern-deedy' or 'awesome-cv'"
            )

        # Output backend selection
        self.output_backend = os.getenv("OUTPUT_BACKEND", "weasyprint").lower()
        if self.output_backend not in ["latex", "weasyprint"]:
            raise ValueError(
                f"Unknown output backend: {self.output_backend}. "
                "Use 'latex' or 'weasyprint'"
            )

        # WeasyPrint template settings
        self.template_name = os.getenv("TEMPLATE_NAME", "resume.html.j2")
        self.css_file = os.getenv("CSS_FILE", "resume.css")

        # Template files directory
        self.template_files_dir = Path("templates")

        # Pipeline parameters
        self.top_k_heuristic = int(os.getenv("TOP_K_HEURISTIC", "20"))
        self.top_k_final = int(os.getenv("TOP_K_FINAL", "12"))
        self.critique_threshold = float(os.getenv("CRITIQUE_THRESHOLD", "0.80"))
        self.max_critique_loops = int(os.getenv("MAX_CRITIQUE_LOOPS", "2"))
        self.escalate_on_second_pass = (
            os.getenv("ESCALATE_ON_SECOND_PASS", "false").lower() == "true"
        )

        # Experience grouping
        self.recent_years_threshold = int(os.getenv("RECENT_YEARS_THRESHOLD", "10"))
        self.current_year = datetime.now().year

        # PDF compilation (only relevant for LaTeX backend)
        self.compile_pdf = os.getenv("COMPILE_PDF", "false").lower() == "true"

        # Cloud uploaders
        self.enable_minio = os.getenv("ENABLE_MINIO", "false").lower() == "true"
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "")
        self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "")
        self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "")
        self.minio_bucket = os.getenv("MINIO_BUCKET", "resumes")

        self.enable_nextcloud = (
            os.getenv("ENABLE_NEXTCLOUD", "false").lower() == "true"
        )
        self.nextcloud_endpoint = os.getenv("NEXTCLOUD_ENDPOINT", "")
        self.nextcloud_user = os.getenv("NEXTCLOUD_USER", "")
        self.nextcloud_password = os.getenv("NEXTCLOUD_PASSWORD", "")

    def get_company_abbreviation(self, company: str) -> str:
        """Get company abbreviation for filename."""
        # Clean company name
        for suffix in [
            ", Inc.",
            " Inc.",
            ", LLC",
            " LLC",
            " Corporation",
            " Corp.",
            " Ltd.",
            " Co.",
        ]:
            company = company.replace(suffix, "")

        # Check known abbreviations
        abbrev = self.COMPANY_ABBREV.get(company)
        if abbrev:
            return abbrev

        # Create abbreviation from first letters or first word
        words = company.split()
        if len(words) > 1:
            return "".join([w[0] for w in words if w]).lower()
        else:
            return words[0].lower() if words else "company"

    def get_title_keywords(self, title: str, max_words: int = 4) -> str:
        """Extract key words from job title."""
        import re

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "of",
            "in",
            "to",
            "for",
            "with",
        }
        words = [w for w in re.findall(r"\w+", title.lower()) if w not in stop_words]
        return "_".join(words[:max_words]) if words else "position"

    def get_output_filename(self, extension: str = "tex") -> str:
        """Generate clean filename (lowercase, no timestamp)."""
        company_abbrev = self.get_company_abbreviation(self.company)
        title_key = self.get_title_keywords(self.job_title)
        return f"{company_abbrev}_{title_key}.{extension}"

    def get_checkpoint_filename(self, name: str) -> str:
        """Get filename for checkpoint (no timestamp)."""
        return f"{name}.json"

    def compute_hash(self, data: dict) -> str:
        """Compute hash for caching."""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]

    def get_output_dir(self) -> Path:
        """Get output directory for this run."""
        date_dir = self.base_output / self.date_stamp
        date_dir.mkdir(parents=True, exist_ok=True)

        run_dir = date_dir / f"run_{self.time_stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create/update 'latest' symlink
        latest_link = date_dir / "latest"
        if latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(run_dir.name)

        return run_dir

    def print_config_summary(self):
        """Print configuration summary for debugging."""
        print("\n" + "=" * 80)
        print("PIPELINE CONFIGURATION")
        print("=" * 80)
        print(f"Job: {self.company} - {self.job_title}")
        print(f"Models: {self.base_model} / {self.strong_model}")
        print(f"Output Backend: {self.output_backend}")
        if self.output_backend == "latex":
            print(f"LaTeX Template: {self.latex_template}")
            print(f"Compile PDF: {self.compile_pdf}")
        else:
            print(f"HTML Template: {self.template_name}")
            print(f"CSS File: {self.css_file}")
        print(f"Caching: {'Enabled' if self.use_cache else 'Disabled'}")
        print(f"Output Directory: {self.output_dir}")
        if self.enable_minio:
            print(f"MinIO Upload: Enabled → {self.minio_bucket}")
        if self.enable_nextcloud:
            print(f"Nextcloud Upload: Enabled → {self.nextcloud_endpoint}")
        print("=" * 80 + "\n")
