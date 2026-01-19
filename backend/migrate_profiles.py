import json
import uuid
from pathlib import Path

# Import DB and Models
from database import Base, SessionLocal, engine
from models import CareerEducation, CareerExperience, CareerProfile, CareerProject, User
from sqlalchemy.orm import Session

# Configuration
BASE_DIR = Path(__file__).parent
PROFILE_PATH = BASE_DIR / "career_profile.json"
DEFAULT_EMAIL = "aaron.t.myers@gmail.com"


def migrate_profile():
    print(f"📂 Reading profile from: {PROFILE_PATH}")

    if not PROFILE_PATH.exists():
        print("❌ Profile file not found!")
        return

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Get Default User
        user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
        if not user:
            print(f"👤 Creating default user: {DEFAULT_EMAIL}")
            user = User(
                id=str(uuid.uuid4()), email=DEFAULT_EMAIL, full_name="Default User"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 2. Load JSON
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        basics = data.get("basics", {})
        location = basics.get("location", {})

        # 3. Create Main Profile Record
        # Check for existing profile to avoid duplicates (optional logic)
        existing = (
            db.query(CareerProfile).filter(CareerProfile.user_id == user.id).first()
        )
        if existing:
            print("⚠️  Profile already exists for this user. Deleting old one...")
            db.delete(existing)
            db.commit()

        print("📝 Inserting Core Profile...")
        profile = CareerProfile(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=basics.get("name", "Unknown"),
            label=basics.get("label"),
            email=basics.get("email"),
            phone=basics.get("phone"),
            url=basics.get("url"),
            summary=basics.get("summary"),
            city=location.get("city"),
            region=location.get("region"),
            country_code=location.get("countryCode"),
            skills=[s.get("name") for s in data.get("skills", []) if s.get("name")],
            languages=[
                l.get("language")
                for l in data.get("languages", [])
                if l.get("language")
            ],
        )

        # Handle Socials
        for p in basics.get("profiles", []):
            net = p.get("network", "").lower()
            if "linkedin" in net:
                profile.linkedin_url = p.get("url")
            elif "github" in net:
                profile.github_url = p.get("url")

        db.add(profile)

        # 4. Insert Work Experience
        print(f"   ↳ Importing {len(data.get('work', []))} work records...")
        for work in data.get("work", []):
            exp = CareerExperience(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                company=work.get("name", ""),
                position=work.get("position", ""),
                start_date=work.get("startDate"),
                end_date=work.get("endDate"),
                summary=work.get("summary"),
                highlights=work.get("highlights", []),
            )
            db.add(exp)

        # 5. Insert Education
        print(f"   ↳ Importing {len(data.get('education', []))} education records...")
        for edu in data.get("education", []):
            ed = CareerEducation(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                institution=edu.get("institution", ""),
                area=edu.get("area"),
                study_type=edu.get("studyType"),
                start_date=edu.get("startDate"),
                end_date=edu.get("endDate"),
                score=edu.get("score"),
                courses=edu.get("courses", []),
            )
            db.add(ed)

        # 6. Insert Projects
        print(f"   ↳ Importing {len(data.get('projects', []))} projects...")
        for proj in data.get("projects", []):
            pr = CareerProject(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                name=proj.get("name", ""),
                description=proj.get("description"),
                url=proj.get("url"),
                keywords=proj.get("keywords", []),
                roles=proj.get("roles", []),
                start_date=proj.get("startDate"),
                end_date=proj.get("endDate"),
            )
            db.add(pr)

        db.commit()
        print("✅ Profile Migration Successful!")

    except Exception as e:
        print(f"❌ Migration Failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    migrate_profile()
