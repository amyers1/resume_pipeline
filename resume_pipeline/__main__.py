"""
CLI entry point for resume generation pipeline.
"""

import argparse
from .pipeline import ResumePipeline
from .config import PipelineConfig


def main():
    """Run the resume generation pipeline from command line."""
    parser = argparse.ArgumentParser(
        description="AI Resume Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s jobs/dcs_position.json career_profile.json
  %(prog)s jobs/job.json career_profile.json --template awesome-cv
  %(prog)s jobs/job.json career_profile.json --compile-pdf
  %(prog)s jobs/job.json career_profile.json --upload-gdrive --gdrive-folder "Resumes"
        """
    )

    parser.add_argument(
        "job_json",
        help="Path to job description JSON file"
    )
    parser.add_argument(
        "career_profile",
        help="Path to career profile JSON file"
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "--template",
        default="modern-deedy",
        choices=["modern-deedy", "awesome-cv"],
        help="LaTeX template to use (default: modern-deedy)"
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="Base model for pipeline (default: gpt-5-mini)"
    )
    parser.add_argument(
        "--strong-model",
        default="gpt-5",
        help="Strong model for critical steps (default: gpt-5)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (force fresh generation)"
    )
    parser.add_argument(
        "--compile-pdf",
        action="store_true",
        help="Compile LaTeX to PDF using xelatex/pdflatex"
    )
    parser.add_argument(
        "--upload-gdrive",
        action="store_true",
        help="Upload PDF and LaTeX to Google Drive"
    )
    parser.add_argument(
        "--gdrive-folder",
        default="Resumes",
        help="Google Drive folder name (default: Resumes)"
    )
    parser.add_argument(
        "--gdrive-credentials",
        default="credentials.json",
        help="Path to Google OAuth2 credentials JSON (default: credentials.json)"
    )
    parser.add_argument(
        "--gdrive-token",
        default="token.json",
        help="Path to save/load Google Drive token (default: token.json)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 2.0.0"
    )
    parser.add_argument(
        "--from-json",
        help="Path to an existing structured_resume.json to compile (skips AI pipeline)"
    )

    args = parser.parse_args()

    # Create configuration
    config = PipelineConfig(
        job_json_path=args.job_json,
        career_profile_path=args.career_profile,
        output_dir=args.output_dir,
        template=args.template,
        use_cache=not args.no_cache,
        compile_pdf=args.compile_pdf,
        enable_gdrive_upload=args.upload_gdrive,
        gdrive_folder=args.gdrive_folder,
        gdrive_credentials=args.gdrive_credentials,
        gdrive_token=args.gdrive_token
    )
    config.base_model = args.model
    config.strong_model = args.strong_model

    # Run pipeline
    pipeline = ResumePipeline(config)
    if args.from_json:
        json_path = Path(args.from_json)
        pdf_path = pipeline.compile_existing_json(json_path)
        if pdf_path:
            print(f"\n✓ PDF generated successfully at {pdf_path}")
    else:
        structured_resume, latex_output, pdf_path = pipeline.run()
        print(f"\n✓ Success! Resume generated for {structured_resume.full_name}")


if __name__ == "__main__":
    main()
