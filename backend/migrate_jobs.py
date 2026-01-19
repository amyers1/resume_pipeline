import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

# Import your DB connection and models
# (Assumes this script is run from inside the 'backend' directory)
from database import SessionLocal, engine, Base
from models import Job, User, CareerProfile

# 1. Setup
DEFAULT_EMAIL = "aaron.t.myers@gmail.com"

# Adjust these paths if your files are located elsewhere relative to 'backend/'
BASE_DIR = Path(__file__).parent
JOBS_DIR = BASE_DIR / "jobs"  # Where your existing .json files are
PROFILE_PATH = BASE_DIR / "career_profile.json" # Your main profile

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def load_career_profile():
    """Load the default career profile to attach to historical jobs."""
    if not PROFILE_PATH.exists():
        print(f"⚠️ Warning: Career profile not found at {PROFILE_PATH}. Jobs will have null profiles.")
        return None

    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error reading career profile: {e}")
        return None

def migrate():
    # ... (setup code) ...
    print(f"📂 Looking for job files in: {JOBS_DIR.absolute()}")

    if not JOBS_DIR.exists():
        print("❌ Jobs directory not found!")
        return

    # Create tables if they don't exist (safety check)
    Base.metadata.create_all(bind=engine)

    # 1. Ensure Default User Exists
    db = SessionLocal()
    default_user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()

    if not default_user:
        print(f"👤 Creating default user: {DEFAULT_EMAIL}")
        default_user = User(
            id=str(uuid.uuid4()),
            email=DEFAULT_EMAIL,
            full_name="Default User"
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)

        # 2. Create a default profile for this user from the file
        career_json = load_career_profile()
        if career_json:
            print("📄 Creating default career profile in DB")
            profile = CareerProfile(
                id=str(uuid.uuid4()),
                user_id=default_user.id,
                name="Imported Profile",
                profile_json=career_json
            )
            db.add(profile)
            db.commit()

    print(f"✅ Using User ID: {default_user.id}")

    try:
            # Loop through all .json files in the jobs directory
            for filename in os.listdir(JOBS_DIR):
                if not filename.endswith(".json") or filename == "schema.json":
                    continue

                file_path = JOBS_DIR / filename

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        job_data = json.load(f)

                    # Extract Key Details (Fail gracefully if keys missing)
                    details = job_data.get("job_details", {})
                    company = details.get("company", "Unknown Company")
                    title = details.get("title") or details.get("job_title", "Unknown Title")

                    # Check if job already exists (deduplication based on company+title)
                    # You can remove this check if you want to force import everything
                    existing = db.query(Job).filter(
                        Job.company == company,
                        Job.job_title == title
                    ).first()

                    if existing:
                        print(f"⏭️  Skipping existing: {company} - {title}")
                        continue

                    # Create Job Record (Updated with user_id)
                    new_job = Job(
                        id=str(uuid.uuid4()),
                        user_id=default_user.id,  # <--- LINK HERE
                        company=company,
                        job_title=title,
                        status="imported",
                        job_description_json=job_data,
                        career_profile_json=career_profile,
                        template="awesome-cv",
                        output_backend="weasyprint",
                        priority=5,
                        created_at=datetime.fromtimestamp(file_path.stat().st_mtime)
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

        # Commit all changes
        db.commit()
        print("\n" + "="*30)
        print(f"🎉 Migration Complete!")
        print(f"✅ Successfully imported: {count}")
        print(f"❌ Failed: {errors}")
        print("="*30)

    except Exception as e:
        print(f"CRITICAL DB ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
    # ... (rest of script) ...
