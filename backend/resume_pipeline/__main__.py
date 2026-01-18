"""
CLI entry point for resume generation pipeline.
All configuration now controlled via .env file.
"""

import sys
from pathlib import Path

from .config import PipelineConfig
from .pipeline import ResumePipeline


def main():
    """Run the resume generation pipeline from .env configuration."""
    print("\n🚀 AI Resume Generation Pipeline")
    print("Configuration loaded from .env file\n")

    try:
        # Load configuration from .env
        config = PipelineConfig()

        # Print configuration summary
        config.print_config_summary()

        # Check for --from-json flag for offline compilation
        if len(sys.argv) > 1 and sys.argv[1] == "--from-json":
            if len(sys.argv) < 3:
                print("❌ Error: --from-json requires a path to structured_resume.json")
                print("Usage: python -m resume_pipeline --from-json path/to/structured_resume.json")
                sys.exit(1)

            json_path = Path(sys.argv[2])
            pipeline = ResumePipeline(config)
            pdf_path = pipeline.compile_existing_json(json_path)

            if pdf_path:
                print(f"\n✅ PDF generated successfully: {pdf_path}")
            else:
                print("\n❌ PDF generation failed")
                sys.exit(1)
        else:
            # Run full pipeline
            pipeline = ResumePipeline(config)
            structured_resume, output_artifact, pdf_path = pipeline.run()

            print(f"\n✅ Success! Resume generated for {structured_resume.full_name}")
            print(f"   Company: {config.company}")
            print(f"   Position: {config.job_title}")
            print(f"   Output: {config.output_dir}")

    except FileNotFoundError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\n💡 Make sure you have:")
        print("   1. Created a .env file (copy from .env.example)")
        print("   2. Set JOB_JSON_PATH to your job description file")
        print("   3. Set CAREER_PROFILE_PATH to your career profile")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
