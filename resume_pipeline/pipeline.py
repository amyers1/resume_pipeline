"""
Main resume generation pipeline orchestrator.
Simplified version without Google Drive integration.
"""

import json
from pathlib import Path
from typing import Optional, Tuple

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

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


class ResumePipeline:
    """Main pipeline orchestrator for resume generation."""

    def __init__(self, config: PipelineConfig):
        self.config = config

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
        self.cache = CacheManager(config.cache_dir)
        self.analyzer = JobAnalyzer(self.base_llm)
        self.matcher = AchievementMatcher(self.base_llm, self.strong_llm, config)
        self.draft_gen = DraftGenerator(self.strong_llm, config)
        self.critic = ResumeCritic(self.base_llm, config)
        self.parser = StructuredResumeParser(self.base_llm)
        self.latex_gen = LaTeXGenerator(config.latex_template)

        # Backend selection from config
        self.output_backend = config.output_backend

        # Instantiate appropriate compiler
        CompilerCls = COMPILERS.get(self.output_backend)
        if not CompilerCls:
            raise ValueError(f"Unsupported OUTPUT_BACKEND: {self.output_backend}")

        if self.output_backend == "latex":
            # LaTeX compiler (for .tex generation only, no compilation)
            self.compiler = CompilerCls(
                template_dir=config.template_files_dir,
                fonts_dir=None,  # Not needed since we won't compile
            )
        else:
            # WeasyPrint compiler
            self.compiler = CompilerCls(
                template_dir=config.template_files_dir,
                css_file=config.css_file,
            )

        # Initialize uploaders (no Google Drive)
        self.minio = None
        if config.enable_minio:
            self.minio = MinioUploader(
                config.minio_endpoint,
                config.minio_access_key,
                config.minio_secret_key,
                config.minio_bucket,
            )

        self.nextcloud = None
        if config.enable_nextcloud:
            self.nextcloud = NextcloudUploader(
                config.nextcloud_endpoint,
                config.nextcloud_user,
                config.nextcloud_password,
            )

    def run(self) -> Tuple[StructuredResume, str, Optional[Path]]:
        """
        Execute the full resume generation pipeline.

        Returns:
            Tuple of (structured_resume, raw_output, pdf_path)
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
                "matched_achievements", [a.model_dump() for a in matched_achievements]
            )

            # Step 4: Generate draft
            print("[4/7] Generating draft resume...")
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
        print("[5/7] Critiquing and refining resume...")
        final_resume, critique = self.critic.critique_and_refine(
            draft_resume, jd_requirements
        )
        self._save_checkpoint("final_resume", final_resume)
        self._save_checkpoint("critique", critique)

        # Step 6: Generate structured output
        print("[6/7] Generating structured output...")
        structured_resume = self.parser.parse(final_resume)
        self._save_checkpoint("structured_resume", structured_resume.model_dump())

        # Step 7: Generate outputs and upload
        print("[7/7] Post-processing and file generation...")
        pdf_path: Optional[Path] = None
        latex_output = ""

        if self.output_backend == "latex":
            # Generate LaTeX file
            print("  Generating LaTeX (.tex) file...")
            latex_output = self.latex_gen.generate(structured_resume)
            latex_filename = self.config.get_output_filename("tex")
            latex_path = self.config.output_dir / latex_filename
            latex_path.write_text(latex_output, encoding="utf-8")
            print(f"  ✓ LaTeX file created: {latex_filename}")

            # Note: We no longer compile LaTeX to PDF automatically
            # Users can upload .tex to Overleaf or compile manually
            print("  ℹ️  LaTeX compilation skipped (generate .tex only)")
            print("     Upload .tex file to Overleaf or compile manually with:")
            print(f"     xelatex {latex_filename}")

            # Upload .tex file
            self._handle_uploads(latex_path)

            self._print_summary(critique, latex_filename, None)
            return structured_resume, latex_output, None

        else:
            # WeasyPrint backend - generate both PDF and .tex
            print("  Using WeasyPrint for PDF generation...")

            # Generate PDF
            pdf_filename = self.config.get_output_filename("pdf")
            output_pdf = self.config.output_dir / pdf_filename
            context = structured_resume.model_dump()

            pdf_path = self.compiler.compile(
                output_pdf=output_pdf,
                template_name=self.config.template_name,
                context=context,
            )

            # Also generate .tex file for archival/manual compilation
            print("  Also generating LaTeX (.tex) file for archival...")
            latex_output = self.latex_gen.generate(structured_resume)
            latex_filename = self.config.get_output_filename("tex")
            latex_path = self.config.output_dir / latex_filename
            latex_path.write_text(latex_output, encoding="utf-8")
            print(f"  ✓ LaTeX file created: {latex_filename}")

            # Upload both PDF and .tex
            if pdf_path:
                self._handle_uploads(pdf_path)
            self._handle_uploads(latex_path)

            self._print_summary(critique, latex_filename, pdf_path)
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

        return pdf_path

    def _handle_uploads(self, file_path: Path):
        """Handle cloud storage uploads."""
        if not file_path or not file_path.exists():
            return

        print(f"\n  [Upload] Processing {file_path.name}...")

        # MinIO upload
        if self.minio and self.minio.enabled:
            remote_path = f"{self.config.date_stamp}/{file_path.name}"
            self.minio.upload_file(file_path, remote_path)

        # Nextcloud upload
        if self.nextcloud and self.nextcloud.enabled:
            remote_dir = f"Resumes/{self.config.date_stamp}"
            self.nextcloud.upload_file(file_path, remote_dir)

    def _load_json(self, path: Path) -> dict:
        """Load JSON file."""
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_checkpoint(self, name: str, data):
        """Save intermediate pipeline state."""
        filename = self.config.get_checkpoint_filename(name)
        path = self.config.output_dir / filename
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
        print(f"Output Directory: {self.config.output_dir}")
        print(f"\nGenerated Files:")
        print(f"  • LaTeX: {latex_filename}")
        if pdf_path:
            print(f"  • PDF: {pdf_path.name}")
        print(f"{'=' * 80}\n")
