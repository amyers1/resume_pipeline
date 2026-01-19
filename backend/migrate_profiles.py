import json
import re
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


def parse_education_string(edu_str):
    """
    Parses strings like:
    "M.S., Electrical Engineering – Air Force Institute of Technology, WPAFB, OH (2013)"
    into dictionary fields.
    """
    try:
        # Split by the dash to separate Degree/Major from School/Location/Year
        parts = edu_str.split(" – ")
        if len(parts) < 2:
            return {"institution": edu_str}

        degree_part = parts[0].strip()
        school_part = parts[1].strip()

        # Parse Degree and Major (e.g., "M.S., Electrical Engineering")
        degree_split = degree_part.split(", ", 1)
        study_type = degree_split[0]
        area = degree_split[1] if len(degree_split) > 1 else None

        # Parse Year (e.g., "... (2013)")
        year_match = re.search(r"\((\d{4})\)", school_part)
        end_date = year_match.group(1) if year_match else None

        # Remove year from school string
        institution = school_part.split(" (")[0].strip()

        return {
            "institution": institution,
            "study_type": study_type,
            "area": area,
            "end_date": end_date,
        }
    except Exception:
        # Fallback if format doesn't match
        return {"institution": edu_str}


def migrate_profile():
    print(f"📂 Reading profile from: {PROFILE_PATH}")

    if not PROFILE_PATH.exists():
        print("❌ Profile file not found!")
        return

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Get/Create Default User
        user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
        if not user:
            print(f"👤 Creating default user: {DEFAULT_EMAIL}")
            user = User(
                id=str(uuid.uuid4()), email=DEFAULT_EMAIL, full_name="Aaron T. Myers"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 2. Load JSON
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 3. Construct Profile Summary
        # Since the JSON has separate lists for awards/certs, we combine them into the text summary
        # so they are visible to the LLM when it reads the profile.
        summary_lines = []
        if data.get("clearance"):
            summary_lines.append(f"Clearance: {data['clearance']}")

        if data.get("certifications"):
            summary_lines.append("\nCertifications:")
            for c in data["certifications"]:
                summary_lines.append(f"- {c}")

        if data.get("awards"):
            summary_lines.append("\nAwards:")
            for a in data["awards"]:
                summary_lines.append(f"- {a}")

        full_summary = "\n".join(summary_lines)

        # 4. Create Main Profile Record
        # Check for existing profile to avoid duplicates
        existing = (
            db.query(CareerProfile).filter(CareerProfile.user_id == user.id).first()
        )
        if existing:
            print("⚠️  Profile already exists. Deleting old one to refresh data...")
            db.delete(existing)
            db.commit()

        print("📝 Inserting Core Profile...")
        profile = CareerProfile(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=data.get("full_name", "Aaron T. Myers"),
            label=data.get(
                "clearance"
            ),  # Storing clearance in label as a quick reference
            email=DEFAULT_EMAIL,
            summary=full_summary,
            # Map "core_domains" to skills
            skills=data.get("core_domains", []),
        )
        db.add(profile)

        # 5. Insert Work Experience (Roles)
        roles = data.get("roles", [])
        print(f"   ↳ Importing {len(roles)} work roles...")

        for role in roles:
            # Flatten achievements into bullet points
            highlights = []
            for ach in role.get("achievements", []):
                # Format: Description [Impact: Metric]
                text = ach.get("description", "")
                metric = ach.get("impact_metric")
                if metric:
                    text += f" [Impact: {metric}]"
                highlights.append(text)

            exp = CareerExperience(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                company=role.get("organization", ""),
                position=role.get("title", ""),
                start_date=role.get("start_date"),
                end_date=role.get("end_date"),
                # Store location and seniority in summary since they don't have dedicated columns
                summary=f"Location: {role.get('location')} | Seniority: {role.get('seniority')}",
                highlights=highlights,
            )
            db.add(exp)

        # 6. Insert Education
        education_list = data.get("education", [])
        print(f"   ↳ Importing {len(education_list)} education records...")

        for edu_str in education_list:
            parsed = parse_education_string(edu_str)

            ed = CareerEducation(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                institution=parsed.get("institution", ""),
                area=parsed.get("area"),
                study_type=parsed.get("study_type"),
                end_date=parsed.get("end_date"),
            )
            db.add(ed)

        # 7. Commit Transaction
        db.commit()
        print("✅ Profile Migration Successful!")

    except Exception as e:
        print(f"❌ Migration Failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    migrate_profile()
