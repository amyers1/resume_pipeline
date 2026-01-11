"""
Main resume generation pipeline orchestrator.
"""

import json
import os
from pathlib import Path
from typing import Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import CareerProfile, StructuredResume, CachedPipelineState
from .config import PipelineConfig
from .cache import CacheManager
from .analyzers.job_analyzer import JobAnalyzer
from .matchers.achievement_matcher import AchievementMatcher
from .generators.draft_generator import DraftGenerator
from .generators.latex_generator import LaTeXGenerator, StructuredResumeParser
from .critics.resume_critic import ResumeCritic
from .compilers import COMPILERS
from .uploaders.gdrive_uploader import GoogleDriveUploader
from .uploaders.minio_uploader import MinioUploader
# from .uploaders.nextcloud_uploader import NextcloudUploader


class ResumePipeline:
    """Main pipeline orchestrator for resume generation."""

    def __init__(self, config: PipelineConfig):
        self.config = config

        # Helper to initialize the correct provider
        def get_model(model_name: str, temperature: float):
            if "gemini" in model_name.lower():
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=config.google_api_key,
                    temperature=temperature
                )
            else:
                return ChatOpenAI(
                    model=model_name,
                    api_key=config.openai_api_key,
                    temperature=temperature
                )

        # Initialize LLMs
        self.base_llm = get_model(config.base_model, 0.1)
        self.strong_llm = get_model(config.strong_model, 0.1)

        # Initialize components
        self.cache = CacheManager(config.cache_dir)
        self.analyzer = JobAnalyzer(self.base_llm)
        self.matcher = AchievementMatcher(self.base_llm, self.strong_llm, config)
        self.draft_gen = DraftGenerator(self.strong_llm, config)
        self.critic = ResumeCritic(self.base_llm, config)
        self.parser = StructuredResumeParser(self.base_llm)
        self.latex_gen = LaTeXGenerator(config.template)

        # Backend selection from environment
        self.output_backend = os.getenv("OUTPUT_BACKEND", "latex").lower()
        self.template_name = os.getenv("TEMPLATE_NAME", "resume.html.j2")
        self.css_file = os.getenv("CSS_FILE", "resume.css")
        # Optional override; otherwise use config.get_output_filename()
        self.output_path_env = os.getenv("OUTPUT_PATH", "")

        # Instantiate appropriate compiler
        CompilerCls = COMPILERS.get(self.output_backend)
        if not CompilerCls:
            raise ValueError(f"Unsupported OUTPUT_BACKEND: {self.output_backend}")

        if self.output_backend == "latex":
            # Match existing LaTeXCompiler signature
            self.compiler = CompilerCls(
                template_dir=config.template_files_dir,
                fonts_dir=config.fonts_dir,
            )
        else:
            # WeasyPrintCompiler(template_dir, css_file)
            self.compiler = CompilerCls(
                template_dir=config.template_files_dir,
                css_file=self.css_file,
            )

        # Initialize uploader if enabled
        self.uploader = None
        if config.enable_gdrive_upload:
            self.uploader = GoogleDriveUploader(
                credentials_file=config.gdrive_credentials,
                token_file=config.gdrive_token
            )

        if config.enable_minio:
            self.minio = MinioUploader(config.minio_endpoint, config.minio_access_key,
                                       config.minio_secret_key, config.minio_bucket)

        if config.enable_nextcloud:
            self.nextcloud = NextcloudUploader(config.nextcloud_endpoint, config.nextcloud_user,
                                               config.nextcloud_password)

    def run(self) -> Tuple[StructuredResume, str, Optional[Path]]:
        """
        Execute the full resume generation pipeline.

        Returns:
            Tuple of (structured_resume, raw_output, pdf_path)

            raw_output:
                - LaTeX source if backend == 'latex'
                - Final refined resume text (or JSON) if backend == 'weasyprint'
        """
        print("=" * 80)
        print("RESUME GENERATION PIPELINE")
        print("=" * 80)

        # Step 1: Load inputs
        print("\n[1/7] Loading job description and career profile...")
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
            print("  ✓ Using cached job analysis, matching, and draft")
            jd_requirements = cached_state.jd_requirements
            matched_achievements = cached_state.matched_achievements
            draft_resume = cached_state.draft_resume
        else:
            # Step 2: Analyze JD
            print("[2/7] Analyzing job requirements...")
            jd_requirements = self.analyzer.analyze(jd_json)
            self._save_checkpoint("jd_requirements", jd_requirements.model_dump())

            # Step 3: Match achievements
            print("[3/7] Matching achievements to job requirements...")
            matched_achievements = self.matcher.match(jd_requirements, career_profile)
            self._save_checkpoint(
                "matched_achievements",
                [a.model_dump() for a in matched_achievements]
            )

            # Step 4: Generate draft
            print("[4/7] Generating draft resume...")
            draft_resume = self.draft_gen.generate(
                jd_requirements, career_profile, matched_achievements
            )
            self._save_checkpoint("draft_resume", draft_resume)

            # Save to cache
            if self.config.use_cache:
                self.cache.save(cache_key, CachedPipelineState(
                    job_hash=job_hash,
                    career_hash=career_hash,
                    jd_requirements=jd_requirements,
                    matched_achievements=matched_achievements,
                    draft_resume=draft_resume,
                    timestamp=self.config.full_timestamp
                ))

        # Step 5: Critique and refine (always run for iteration)
        print("[5/7] Critiquing and refining resume...")
        final_resume, critique = self.critic.critique_and_refine(
            draft_resume, jd_requirements
        )
        self._save_checkpoint("final_resume", final_resume)
        self._save_checkpoint("critique", critique)

        # Step 6: Generate structured output and source artifact
        print("[6/7] Generating structured output...")
        structured_resume = self.parser.parse(final_resume)
        self._save_checkpoint("structured_resume", structured_resume.model_dump())

        pdf_path: Optional[Path] = None

        if self.output_backend == "latex":
            # Existing behavior: generate LaTeX, then compile
            print("  Using LaTeX backend...")
            latex_output = self.latex_gen.generate(structured_resume)
            latex_filename = self.config.get_output_filename("tex")
            latex_path = self.config.output_dir / latex_filename
            latex_path.write_text(latex_output, encoding="utf-8")

            # Step 7: Compile to PDF and upload
            print("[7/7] Post-processing (LaTeX)...")
            if self.config.compile_pdf:
                engine = self.compiler.get_recommended_engine(self.config.template)
                pdf_path = self.compiler.compile(latex_path, engine=engine)

            # Upload to Google Drive
            if self.uploader and self.uploader.enabled:
                self._upload_files(latex_path, pdf_path)

            self._print_summary(critique, latex_filename, pdf_path)

            return structured_resume, latex_output, pdf_path

        else:
            # New behavior: HTML/Jinja + WeasyPrint
            print("  Using WeasyPrint backend...")
            # Decide output path
            if self.output_path_env:
                output_pdf = Path(self.output_path_env)
            else:
                pdf_filename = self.config.get_output_filename("pdf")
                output_pdf = self.config.output_dir / pdf_filename

            # Template name / CSS are read in __init__ via env
            template_name = self.template_name

            # Compile directly to PDF from structured_resume
            print("[7/7] Post-processing (WeasyPrint)...")

            # Convert structured_resume to a plain dict for Jinja context
            context = structured_resume.model_dump()

            # The WeasyPrintCompiler.compile API:
            # compile(output_pdf: Path, template_name: str, context: Dict[str, Any], clean: bool = False)
            pdf_path = self.compiler.compile(
                output_pdf=output_pdf,
                template_name=template_name,
                context=context,
            )

            # There is no LaTeX file in this branch
            latex_filename = "(none – WeasyPrint)"
            latex_output = final_resume  # return the refined text as "raw output"

            # Upload to Google Drive (PDF only)
            if self.uploader and self.uploader.enabled and pdf_path:
                self._upload_files_for_weasyprint(pdf_path)

            self._print_summary(critique, latex_filename, pdf_path)

            return structured_resume, latex_output, pdf_path

    def compile_existing_json(self, json_path: Path) -> Optional[Path]:
        """Compiles an existing structured_resume.json to PDF without running AI steps."""
        print(f"\n[Offline Mode] Compiling PDF from: {json_path}")

        if not json_path.exists():
            print(f"  ✗ Error: File not found at {json_path}")
            return None

        # Load the existing structured data
        with open(json_path, 'r', encoding='utf-8') as f:
            context = json.load(f)

        # Determine output path (matches your existing run logic)
        if self.output_path_env:
            output_pdf = Path(self.output_path_env)
        else:
            # Use the filename from config but ensure it's in the same dir as the JSON
            pdf_filename = self.config.get_output_filename("pdf")
            output_pdf = json_path.parent / pdf_filename

        # Compile via WeasyPrint
        pdf_path = self.compiler.compile(
            output_pdf=output_pdf,
            template_name=self.template_name,
            context=context,
        )

        return pdf_path

    # Optional helper specialized for WeasyPrint branch
    def _upload_files_for_weasyprint(self, pdf_path: Optional[Path]):
        """Upload PDF-only output to Google Drive for WeasyPrint backend."""
        if not self.uploader or not self.uploader.enabled or not pdf_path:
            return

        print("\n  Uploading to Google Drive...")

        folder_id = None
        if self.config.gdrive_folder:
            base_folder = self.uploader.get_or_create_folder(
                self.config.gdrive_folder
            )
            if base_folder:
                date_folder = self.uploader.get_or_create_folder(
                    self.config.date_stamp,
                    parent_id=base_folder
                )
                folder_id = date_folder

        if pdf_path.exists():
            self.uploader.upload_file(pdf_path, folder_id=folder_id)

    def _upload_to_all_destinations(self, pdf_path: Path):
        # Google Drive (Existing)
        if self.uploader and self.uploader.enabled:
            self._upload_files_for_weasyprint(pdf_path)

        # MinIO
        if hasattr(self, 'minio') and self.minio.enabled:
            remote_name = f"{self.config.date_stamp}/{pdf_path.name}"
            self.minio.upload_file(pdf_path, remote_name)

        # Nextcloud
        if hasattr(self, 'nextcloud') and self.nextcloud.enabled:
            remote_dir = f"Resumes/{self.config.date_stamp}"
            self.nextcloud.upload_file(pdf_path, remote_dir)

        # Upload LaTeX file
        self.uploader.upload_file(latex_path, folder_id=folder_id)

        # Upload PDF if available
        if pdf_path and pdf_path.exists():
            self.uploader.upload_file(pdf_path, folder_id=folder_id)

    def _load_json(self, path: Path) -> dict:
        """Load JSON file."""
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_checkpoint(self, name: str, data):
        """Save intermediate pipeline state."""
        filename = self.config.get_checkpoint_filename(name)
        path = self.config.output_dir / filename
        if isinstance(data, str):
            path.write_text(
                json.dumps({"content": data}, indent=2),
                encoding="utf-8"
            )
        else:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _print_summary(self, critique: dict, latex_filename: str, pdf_path: Optional[Path]):
        """Print pipeline completion summary."""
        print(f"\n✓ Pipeline complete!")
        print(f"  Final score: {critique.get('score', 'N/A')}")
        print(f"  Company: {self.config.company}")
        print(f"  Position: {self.config.job_title}")
        print(f"  Template: {self.config.template}")
        print(f"  Output directory: {self.config.output_dir}")
        print(f"  LaTeX file: {latex_filename}")
        if pdf_path:
            print(f"  PDF file: {pdf_path.name}")
        print("=" * 80)
