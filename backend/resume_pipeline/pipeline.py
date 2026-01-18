"""
Main resume generation pipeline orchestrator.
Simplified version without Google Drive integration.
"""

import json
import logging
from pathlib import Path
from typing import Callable, Optional, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# ... Keep existing imports ...
from .analyzers.job_analyzer import JobAnalyzer
from .cache import CacheManager
from .compilers import COMPILERS
from .config import PipelineConfig
from .critics.resume_critic import ResumeCritic
from .generators.draft_generator import DraftGenerator
from .generators.latex_generator import LaTeXGenerator, StructuredResumeParser
from .matchers.achievement_matcher import AchievementMatcher
from .models import CachedPipelineState, CareerProfile, StructuredResume
from .uploaders.minio_uploader import MinioUploader
from .uploaders.nextcloud_uploader import NextcloudUploader

# Configure Logger
logger = logging.getLogger(__name__)


class ResumePipeline:
    """Main pipeline orchestrator for resume generation."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.run_dir = self.config.get_output_dir()

        # New: Progress Callback
        self.progress_callback: Optional[Callable[[str, int, str], None]] = None

        # Helper to initialize the correct LLM provider
        def get_model(model_name: str, temperature: float):
            if "gemini" in model_name.lower():
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=config.google_api_key,
                    temperature=temperature,
                )
            return ChatOpenAI(
                model=model_name,
                api_key=config.openai_api_key,
                temperature=temperature,
            )

        # Initialize LLMs
        self.base_llm = get_model(config.base_model, 0.1)
        self.strong_llm = get_model(config.strong_model, 0.1)

        # Initialize components
        self.cache = CacheManager(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            ttl_days=config.redis_cache_ttl_days,
        )
        self.analyzer = JobAnalyzer(self.base_llm)
        self.matcher = AchievementMatcher(self.base_llm, self.strong_llm, config)
        self.draft_gen = DraftGenerator(self.strong_llm, config)
        self.critic = ResumeCritic(self.base_llm, config)
        self.parser = StructuredResumeParser(self.base_llm)
        self.latex_gen = LaTeXGenerator(config.latex_template)

        # Backend selection
        self.output_backend = config.output_backend

        # Instantiate compiler
        CompilerCls = COMPILERS.get(self.output_backend)
        if not CompilerCls:
            raise ValueError(f"Unsupported OUTPUT_BACKEND: {self.output_backend}")

        if self.output_backend == "latex":
            self.compiler = CompilerCls(
                template_dir=config.template_files_dir,
                fonts_dir=None,
            )
        else:
            self.compiler = CompilerCls(
                template_dir=config.template_files_dir,
                css_file=config.css_file,
            )

        # Initialize uploaders
        self.minio = None
        if config.enable_minio:
            self.minio = MinioUploader(
                config.minio_endpoint,
                config.minio_access_key,
                config.minio_secret_key,
                config.minio_bucket,
            )

        self.nextcloud = None
        if config.enable_nextcloud and config.nextcloud_endpoint:
            self.nextcloud = NextcloudUploader(
                config.nextcloud_endpoint,
                config.nextcloud_user,
                config.nextcloud_password,
            )

    # NEW: Method called by Worker
    def set_progress_callback(self, callback: Callable[[str, int, str], None]):
        """Set a callback function to report progress updates."""
        self.progress_callback = callback

    # NEW: Internal helper
    def _report_progress(self, stage: str, percent: int, message: str):
        """Send progress update if callback is configured."""
        logger.info(f"[{percent}%] {stage}: {message}")
        if self.progress_callback:
            try:
                self.progress_callback(stage, percent, message)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

    def run(self) -> Tuple[StructuredResume, str, Optional[Path]]:
        """
        Execute the full resume generation pipeline.
        """
        logger.info("Starting Resume Generation Pipeline")
        self._report_progress("analyzing_jd", 5, "Loading inputs")

        # Step 1: Load inputs
        jd_json = self._load_json(self.config.job_json_path)
        career_profile = CareerProfile.model_validate_json(
            self.config.career_profile_path.read_text(encoding="utf-8")
        )

        # Compute hashes for caching
        job_hash = self.config.compute_hash(jd_json)
        career_hash = self.config.compute_hash(career_profile.model_dump())
        cache_key = f"{job_hash}_{career_hash}"

        # Try to load from cache
        cached_state = None
        if self.config.use_cache:
            cached_state = self.cache.load(cache_key)

        if cached_state:
            logger.info("Using cached pipeline state")
            self._report_progress("generating_draft", 50, "Restored cached draft")
            jd_requirements = cached_state.jd_requirements
            matched_achievements = cached_state.matched_achievements
            draft_resume = cached_state.draft_resume
        else:
            # Step 2: Analyze JD
            self._report_progress("analyzing_jd", 15, "Analyzing job requirements")
            jd_requirements = self.analyzer.analyze(jd_json)
            self._save_checkpoint("jd_requirements", jd_requirements.model_dump())

            # Step 3: Match achievements
            self._report_progress("matching_achievements", 30, "Matching achievements")
            matched_achievements = self.matcher.match(jd_requirements, career_profile)
            self._save_checkpoint(
                "matched_achievements", [a.model_dump() for a in matched_achievements]
            )

            # Step 4: Generate draft
            self._report_progress("generating_draft", 45, "Generating draft resume")
            draft_resume = self.draft_gen.generate(
                jd_requirements, career_profile, matched_achievements
            )
            self._save_checkpoint("draft_resume", draft_resume)

            # Save to cache
            if self.config.use_cache:
                self.cache.save(
                    cache_key,
                    CachedPipelineState(
                        job_hash=job_hash,
                        career_hash=career_hash,
                        jd_requirements=jd_requirements,
                        matched_achievements=matched_achievements,
                        draft_resume=draft_resume,
                        timestamp=self.config.full_timestamp,
                    ),
                )

        # Step 5: Critique and refine
        self._report_progress("critiquing", 70, "Critiquing and refining")
        final_resume, critique = self.critic.critique_and_refine(
            draft_resume, jd_requirements
        )
        self._save_checkpoint("final_resume", final_resume)
        self._save_checkpoint("critique", critique)

        # Step 6: Generate structured output
        self._report_progress("refining", 85, "Structuring data")
        structured_resume = self.parser.parse(final_resume)
        self._save_checkpoint("structured_resume", structured_resume.model_dump())

        # Step 7: Generate outputs and upload
        self._report_progress("generating_output", 90, "Compiling final documents")
        pdf_path: Optional[Path] = None
        latex_output = ""

        if self.output_backend == "latex":
            # Generate LaTeX file
            latex_output = self.latex_gen.generate(structured_resume)
            latex_filename = self.config.get_output_filename("tex")
            latex_path = self.run_dir / latex_filename
            latex_path.write_text(latex_output, encoding="utf-8")

            self._handle_uploads(latex_path)
            self._report_progress("completed", 100, "LaTeX generation complete")
            return structured_resume, latex_output, None

        else:
            # WeasyPrint backend
            # Generate PDF
            pdf_filename = self.config.get_output_filename("pdf")
            output_pdf = self.run_dir / pdf_filename
            context = structured_resume.model_dump()

            pdf_path = self.compiler.compile(
                output_pdf=output_pdf,
                template_name=self.config.template_name,
                context=context,
            )

            # Also generate .tex file for archival
            latex_output = self.latex_gen.generate(structured_resume)
            latex_filename = self.config.get_output_filename("tex")
            latex_path = self.run_dir / latex_filename
            latex_path.write_text(latex_output, encoding="utf-8")

            # Uploads
            if pdf_path:
                self._handle_uploads(pdf_path)
            self._handle_uploads(latex_path)

            self._report_progress("completed", 100, "PDF generation complete")
            return structured_resume, latex_output, pdf_path

    def compile_existing_json(self, json_path: Path) -> Optional[Path]:
        """Compile an existing structured_resume.json to PDF without running AI."""
        print(f"\n[Offline Mode] Compiling PDF from: {json_path}")

        if not json_path.exists():
            print(f"  ✗ Error: File not found at {json_path}")
            return None

        # Load the existing structured data
        with open(json_path, "r", encoding="utf-8") as f:
            context = json.load(f)

        # Determine output path
        pdf_filename = self.config.get_output_filename("pdf")
        output_pdf = json_path.parent / pdf_filename

        # Compile via WeasyPrint
        pdf_path = self.compiler.compile(
            output_pdf=output_pdf,
            template_name=self.config.template_name,
            context=context,
        )

        if pdf_path:
            self._handle_uploads(pdf_path)

        # Also generate .tex file for archival/manual compilation
        print("  Also generating LaTeX (.tex) file for archival...")
        try:
            structured_resume = StructuredResume(**context)
            latex_output = self.latex_gen.generate(structured_resume)
            latex_filename = self.config.get_output_filename("tex")
            latex_path = self.run_dir / latex_filename
            latex_path.write_text(latex_output, encoding="utf-8")
            print(f"  ✓ LaTeX file created: {latex_filename}")
            if latex_path:
                self._handle_uploads(latex_path)
        except TypeError as e:
            print(f"Error generating latex file...unable to parse {json_path}")

        return pdf_path

    def _handle_uploads(self, file_path: Path):
        """Handle cloud storage uploads."""
        if not file_path or not file_path.exists():
            return

        print(f"\n  [Upload] Processing {file_path.name}...")

        # MinIO upload
        if self.minio and self.minio.enabled:
            # NEW: Include run timestamp in MinIO path
            remote_path = f"{self.config.date_stamp}/run_{self.config.time_stamp}/{file_path.name}"
            self.minio.upload_file(file_path, remote_path)

        # Nextcloud upload
        if self.nextcloud and self.nextcloud.enabled:
            # NEW: Include run timestamp in Nextcloud path
            remote_parent = f"Resumes/{self.config.date_stamp}"
            remote_dir = (
                f"Resumes/{self.config.date_stamp}/run_{self.config.time_stamp}"
            )
            self.nextcloud.upload_file(file_path, remote_parent, remote_dir)

    def _load_json(self, path: Path) -> dict:
        """Load JSON file."""
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_checkpoint(self, name: str, data):
        """Save intermediate pipeline state."""
        filename = self.config.get_checkpoint_filename(name)
        path = self.run_dir / filename
        if isinstance(data, str):
            path.write_text(json.dumps({"content": data}, indent=2), encoding="utf-8")
        else:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _print_summary(
        self, critique: dict, latex_filename: str, pdf_path: Optional[Path]
    ):
        """Print pipeline completion summary."""
        print(f"\n{'=' * 80}")
        print("✅ PIPELINE COMPLETE")
        print(f"{'=' * 80}")
        print(f"Final Score: {critique.get('score', 'N/A')}")
        print(f"Company: {self.config.company}")
        print(f"Position: {self.config.job_title}")
        print(f"Template: {self.config.latex_template}")
        print(f"Output Directory: {self.run_dir}")
        print(f"\nGenerated Files:")
        print(f"  • LaTeX: {latex_filename}")
        if pdf_path:
            print(f"  • PDF: {pdf_path.name}")
        print(f"{'=' * 80}\n")
