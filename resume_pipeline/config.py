"""
Configuration management for resume pipeline.
"""

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

import pytz
from dotenv import load_dotenv


class PipelineConfig:
    """Central configuration for the resume pipeline."""

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

    def __init__(
        self,
        job_json_path: str,
        career_profile_path: str,
        output_dir: str = "./output",
        template: str = "modern-deedy",
        use_cache: bool = True,
        compile_pdf: bool = False,
        enable_gdrive_upload: bool = False,
        gdrive_credentials: str = "credentials.json",
        gdrive_folder: str = "Resumes",
        gdrive_token: str = "token.json",
    ):
        load_dotenv()

        # API Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

        self.base_model = os.getenv("MODEL", "gemini-1.5-flash")
        self.strong_model = os.getenv("STRONG_MODEL", "gemini-1.5-pro")

        # Conditional validation
        if "gemini" in self.base_model or "gemini" in self.strong_model:
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")

        if "gpt" in self.base_model or "gpt" in self.strong_model:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")

        # Timestamp for directory organization
        est = pytz.timezone("America/New_York")
        now = datetime.now(est)
        self.date_stamp = now.strftime("%Y%m%d")
        self.time_stamp = now.strftime("%H%M%S")
        self.full_timestamp = now.strftime("%Y%m%d_%H%M%S")

        # Load job JSON
        self.job_json_path = Path(job_json_path)
        job_json = json.loads(self.job_json_path.read_text(encoding="utf-8"))
        job_details = job_json.get("job_details", {})
        self.company = job_details.get("company", "Unknown_Company")
        self.job_title = job_details.get("job_title", "Unknown_Position")

        # Paths - NEW: Create run subdirectory within date directory
        self.career_profile_path = Path(career_profile_path)
        base_output = Path(output_dir)

        # Create date-based parent directory
        date_dir = base_output / self.date_stamp
        date_dir.mkdir(parents=True, exist_ok=True)

        # Create time-based run subdirectory
        run_dir = date_dir / f"run_{self.time_stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Set as output directory
        self.output_dir = run_dir

        # Create/update 'latest' symlink to point to this run
        latest_link = date_dir / "latest"
        if latest_link.is_symlink() or latest_link.exists():
            latest_link.unlink()
        try:
            latest_link.symlink_to(run_dir.name)
            print(f"  ✓ Created symlink: {date_dir}/latest -> {run_dir.name}")
        except OSError as e:
            # Symlink creation might fail on some systems; not critical
            print(f"  ⚠ Could not create symlink: {e}")

        # Cache directory (shared across all dates and runs)
        self.cache_dir = base_output / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.use_cache = use_cache

        # Template selection
        self.template = template.lower()
        if self.template not in ["modern-deedy", "awesome-cv"]:
            raise ValueError(
                f"Unknown template: {template}. Choose 'modern-deedy' or 'awesome-cv'."
            )

        # PDF compilation
        self.compile_pdf = compile_pdf

        # Google Drive settings
        self.enable_gdrive_upload = enable_gdrive_upload
        self.gdrive_folder = gdrive_folder
        self.gdrive_credentials = gdrive_credentials
        self.gdrive_token = gdrive_token

    def get_company_abbreviation(self, company: str, max_length: int = 4) -> str:
        """Get abbreviated company name for filenames."""
        # Check predefined abbreviations
        if company in self.COMPANY_ABBREV:
            return self.COMPANY_ABBREV[company]

        # Generate abbreviation dynamically
        words = company.lower().split()
        if len(words) == 1:
            return words[0][:max_length]

        # Take first letter of each word
        abbrev = "".join(w[0] for w in words if w)
        return abbrev[:max_length] if abbrev else "company"

    def get_title_keywords(self, title: str, max_words: int = 4) -> str:
        """Extract key words from job title for filename."""
        # Remove common words
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
