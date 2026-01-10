"""
Configuration management for resume pipeline.
"""

import json
import os
import hashlib
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import pytz


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
        gdrive_folder: str = "Resumes",
        gdrive_credentials: str = "credentials.json",
        gdrive_token: str = "token.json"
    ):
        load_dotenv()

        # API Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.base_model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.strong_model = "gpt-5"

        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        # Timestamp for directory organization
        est = pytz.timezone('America/New_York')
        now = datetime.now(est)
        self.date_stamp = now.strftime('%Y%m%d')
        self.full_timestamp = now.strftime('%Y%m%d_%H%M%S')

        # Load job JSON
        self.job_json_path = Path(job_json_path)
        job_json = json.loads(self.job_json_path.read_text(encoding="utf-8"))
        job_details = job_json.get("job_details", {})
        self.company = job_details.get("company", "Unknown_Company")
        self.job_title = job_details.get("job_title", "Unknown_Position")

        # Paths
        self.career_profile_path = Path(career_profile_path)
        base_output = Path(output_dir)
        self.output_dir = base_output / self.date_stamp
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cache directory (shared across dates)
        self.cache_dir = base_output / ".cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.use_cache = use_cache

        # Template selection
        self.template = template.lower()
        if self.template not in ["modern-deedy", "awesome-cv"]:
            raise ValueError(
                f"Unknown template: {template}. Use 'modern-deedy' or 'awesome-cv'"
            )

        # Pipeline parameters
        self.top_k_heuristic = 20
        self.top_k_final = 12
        self.critique_threshold = 0.80
        self.max_critique_loops = 2
        self.escalate_on_second_pass = False

        # Experience grouping
        self.recent_years_threshold = 10
        self.current_year = datetime.now().year

        # PDF compilation
        self.compile_pdf = compile_pdf
        self.template_files_dir = Path("templates")  # Directory with .cls files
        self.fonts_dir = Path("fonts")  # Optional custom fonts directory

        # Google Drive upload
        self.enable_gdrive_upload = enable_gdrive_upload
        self.gdrive_folder = gdrive_folder
        self.gdrive_credentials = gdrive_credentials
        self.gdrive_token = gdrive_token

    def get_company_abbreviation(self, company: str) -> str:
        """Get company abbreviation for filename."""
        # Clean company name
        for suffix in [", Inc.", " Inc.", ", LLC", " LLC", " Corporation", " Corp.", " Ltd.", " Co."]:
            company = company.replace(suffix, "")

        # Check known abbreviations
        abbrev = self.COMPANY_ABBREV.get(company)
        if abbrev:
            return abbrev

        # Create abbreviation from first letters or first word
        words = company.split()
        if len(words) > 1:
            return ''.join([w[0] for w in words if w]).lower()
        else:
            return words[0].lower() if words else "company"

    def get_title_keywords(self, title: str, max_words: int = 4) -> str:
        """Extract key words from job title."""
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'of', 'in', 'to', 'for', 'with'}
        words = [w for w in re.findall(r'\w+', title.lower()) if w not in stop_words]
        return '_'.join(words[:max_words]) if words else "position"

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
