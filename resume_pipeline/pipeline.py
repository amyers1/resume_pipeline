"""
Main resume generation pipeline orchestrator.
"""

import json
from pathlib import Path
from typing import Tuple, Optional
from langchain_openai import ChatOpenAI

from .models import CareerProfile, StructuredResume, CachedPipelineState
from .config import PipelineConfig
from .cache import CacheManager
from .analyzers.job_analyzer import JobAnalyzer
from .matchers.achievement_matcher import AchievementMatcher
from .generators.draft_generator import DraftGenerator
from .generators.latex_generator import LaTeXGenerator, StructuredResumeParser
from .critics.resume_critic import ResumeCritic
from .compilers.latex_compiler import LaTeXCompiler
from .uploaders.gdrive_uploader import GoogleDriveUploader


class ResumePipeline:
    """Main pipeline orchestrator for resume generation."""

    def __init__(self, config: PipelineConfig):
        self.config = config

        # Initialize LLMs
        self.base_llm = ChatOpenAI(model=config.base_model, temperature=0.1)
        self.strong_llm = ChatOpenAI(model=config.strong_model, temperature=0.1)

        # Initialize components
        self.cache = CacheManager(config.cache_dir)
        self.analyzer = JobAnalyzer(self.base_llm)
        self.matcher = AchievementMatcher(self.base_llm, self.strong_llm, config)
        self.draft_gen = DraftGenerator(self.strong_llm, config)
        self.critic = ResumeCritic(self.base_llm, config)
        self.parser = StructuredResumeParser(self.base_llm)
        self.latex_gen = LaTeXGenerator(config.template)
        self.compiler = LaTeXCompiler(
            template_dir=config.template_files_dir,
            fonts_dir=config.fonts_dir
        )

        # Initialize uploader if enabled
        self.uploader = None
        if config.enable_gdrive_upload:
            self.uploader = GoogleDriveUploader(
                credentials_file=config.gdrive_credentials,
                token_file=config.gdrive_token
            )

    def run(self) -> Tuple[StructuredResume, str, Optional[Path]]:
        """
        Execute the full resume generation pipeline.

        Returns:
            Tuple of (structured_resume, latex_output, pdf_path)
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

        # Step 6: Generate structured output and LaTeX
        print("[6/7] Generating LaTeX output...")
        structured_resume = self.parser.parse(final_resume)
        self._save_checkpoint("structured_resume", structured_resume.model_dump())

        latex_output = self.latex_gen.generate(structured_resume)
        latex_filename = self.config.get_output_filename("tex")
        latex_path = self.config.output_dir / latex_filename
        latex_path.write_text(latex_output, encoding="utf-8")

        # Step 7: Compile to PDF and upload
        print("[7/7] Post-processing...")
        pdf_path = None

        if self.config.compile_pdf:
            engine = self.compiler.get_recommended_engine(self.config.template)
            pdf_path = self.compiler.compile(latex_path, engine=engine)

        # Upload to Google Drive
        if self.uploader and self.uploader.enabled:
            self._upload_files(latex_path, pdf_path)

        self._print_summary(critique, latex_filename, pdf_path)

        return structured_resume, latex_output, pdf_path

    def _upload_files(self, latex_path: Path, pdf_path: Optional[Path]):
        """Upload files to Google Drive."""
        print("\n  Uploading to Google Drive...")

        # Get or create resume folder structure
        folder_id = None
        if self.config.gdrive_folder:
            # Create date-based subfolder: Resumes/{date}
            base_folder = self.uploader.get_or_create_folder(
                self.config.gdrive_folder
            )
            if base_folder:
                date_folder = self.uploader.get_or_create_folder(
                    self.config.date_stamp,
                    parent_id=base_folder
                )
                folder_id = date_folder

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
