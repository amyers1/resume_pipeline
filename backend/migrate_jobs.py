import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from database import Base, SessionLocal, engine
from models import Job, User
from sqlalchemy.orm import Session

# Configuration
BASE_DIR = Path(__file__).parent
JOBS_DIR = BASE_DIR / "jobs"
PROFILE_PATH = BASE_DIR / "career_profile.json"
DEFAULT_EMAIL = "aaron.t.myers@gmail.com"


def load_career_profile_snapshot():
    """Load the raw JSON to store as a snapshot on the Job record."""
    if not PROFILE_PATH.exists():
        return None
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def safe_int(val):
    """Helper to convert strings/floats to int safely."""
    try:
        return int(val) if val is not None else None
    except:
        return None


def migrate_jobs():
    print(f"📂 Looking for job files in: {JOBS_DIR.absolute()}")

    if not JOBS_DIR.exists():
        print("❌ Jobs directory not found!")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    count = 0
    errors = 0

    try:
        # 1. Get User and Profile Snapshot
        user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
        if not user:
            print(
                "⚠️  User not found. Run migrate_profiles.py first! (Or we will create a placeholder)"
            )
            user = User(
                id=str(uuid.uuid4()), email=DEFAULT_EMAIL, full_name="Default User"
            )
            db.add(user)
            db.commit()

        career_snapshot = load_career_profile_snapshot()

        # 2. Iterate Files
        for filename in os.listdir(JOBS_DIR):
            if not filename.endswith(".json") or filename == "schema.json":
                continue

            file_path = JOBS_DIR / filename

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Unpack Schema Structure
                jd = data.get("job_details", {})
                ben = data.get("benefits", {})
                desc = data.get("job_description", {})
                ctx = jd.get("job_board_list_context", {})

                # Identity Keys
                company = jd.get("company", "Unknown Company")
                title = jd.get("job_title", "Unknown Title")

                # Deduplication
                existing = (
                    db.query(Job)
                    .filter(Job.company == company, Job.job_title == title)
                    .first()
                )

                if existing:
                    print(f"⏭️  Skipping existing: {company} - {title}")
                    continue

                # Create Job
                new_job = Job(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    status="imported",
                    # --- MAPPING SCHEMA TO COLUMNS ---
                    # 1. Details
                    company=company,
                    job_title=title,
                    source=jd.get("source"),
                    platform=jd.get("platform"),
                    company_rating=jd.get("company_rating"),
                    location=jd.get("location"),
                    location_detail=jd.get("location_detail"),
                    employment_type=jd.get("employment_type"),
                    # Pay
                    pay_currency=jd.get("pay_currency", "USD"),
                    pay_min_annual=safe_int(jd.get("pay_min_annual")),
                    pay_max_annual=safe_int(jd.get("pay_max_annual")),
                    pay_rate_type=jd.get("pay_rate_type"),
                    pay_display=jd.get("pay_display"),
                    # Work Model
                    remote_type=jd.get("remote_type"),
                    work_model=jd.get("work_model"),
                    work_model_notes=jd.get("work_model_notes"),
                    # URLs
                    job_post_url=jd.get("job_post_url"),
                    apply_url=jd.get("apply_url"),
                    posting_age=jd.get("posting_age"),
                    # Clearance
                    security_clearance_required=jd.get("security_clearance_required"),
                    security_clearance_preferred=jd.get("security_clearance_preferred"),
                    # Search Context
                    search_keywords=ctx.get("search_keywords"),
                    search_location=ctx.get("search_location"),
                    search_radius=safe_int(ctx.get("search_radius_miles")),
                    # 2. Benefits
                    benefits_listed=ben.get("listed_benefits", []),
                    benefits_text=ben.get("benefits_text"),
                    benefits_eligibility=ben.get("eligibility_notes"),
                    benefits_relocation=ben.get("relocation"),
                    benefits_sign_on_bonus=ben.get("sign_on_bonus"),
                    # 3. Description
                    jd_headline=desc.get("headline"),
                    jd_short_summary=desc.get("short_summary"),
                    jd_full_text=desc.get("full_text"),
                    jd_experience_min=safe_int(
                        desc.get("required_experience_years_min")
                    ),
                    jd_education=desc.get("required_education"),
                    jd_must_have_skills=desc.get("must_have_skills", []),
                    jd_nice_to_have_skills=desc.get("nice_to_have_skills", []),
                    # 4. Config
                    career_profile_json=career_snapshot,  # Snapshot!
                    template="awesome-cv",
                    output_backend="weasyprint",
                    priority=5,
                    created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                )

                db.add(new_job)
                count += 1
                print(f"✅ Imported: {company} - {title}")

            except json.JSONDecodeError:
                print(f"❌ Invalid JSON in file: {filename}")
                errors += 1
            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")
                errors += 1

        db.commit()
        print("\n" + "=" * 30)
        print(f"🎉 Job Migration Complete!")
        print(f"✅ Successfully imported: {count}")
        print(f"❌ Failed: {errors}")
        print("=" * 30)

    except Exception as e:
        print(f"CRITICAL DB ERROR: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    migrate_jobs()
