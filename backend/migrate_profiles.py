import json
import re
import uuid
from pathlib import Path

# Import DB and Models
from database import Base, SessionLocal, engine
from models import (
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerExperienceHighlight,
    CareerProfile,
    CareerProject,
    User,
)
from sqlalchemy.orm import Session

# Configuration
BASE_DIR = Path(__file__).parent
PROFILE_PATH = BASE_DIR / "career_profile.json"
DEFAULT_EMAIL = "aaron.t.myers@gmail.com"


def parse_education_string(edu_str):
    try:
        parts = edu_str.split(" – ")
        if len(parts) < 2:
            return {"institution": edu_str}
        degree_part = parts[0].strip()
        school_part = parts[1].strip()
        degree_split = degree_part.split(", ", 1)
        study_type = degree_split[0]
        area = degree_split[1] if len(degree_split) > 1 else None
        year_match = re.search(r"\((\d{4})\)", school_part)
        end_date = year_match.group(1) if year_match else None
        institution = school_part.split(" (")[0].strip()
        return {
            "institution": institution,
            "study_type": study_type,
            "area": area,
            "end_date": end_date,
        }
    except:
        return {"institution": edu_str}


def parse_cert_string(cert_str):
    """
    Parses "Project Management Professional (PMP), Project Management Institute (2025)"
    """
    try:
        parts = cert_str.split(", ")
        name = parts[0].strip()

        # Look for year at the end
        year_match = re.search(r"\((\d{4})\)$", cert_str)
        date = year_match.group(1) if year_match else None

        # Organization is usually the middle part or last part before year
        org = None
        if len(parts) > 1:
            org = (
                parts[1].replace(f" ({date})", "").strip() if date else parts[1].strip()
            )

        return {"name": name, "organization": org, "date": date}
    except:
        return {"name": cert_str}


def migrate_profile():
    print(f"📂 Reading profile from: {PROFILE_PATH}")
    if not PROFILE_PATH.exists():
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == DEFAULT_EMAIL).first()
        if not user:
            user = User(
                id=str(uuid.uuid4()), email=DEFAULT_EMAIL, full_name="Aaron T. Myers"
            )
            db.add(user)
            db.commit()

        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        existing = (
            db.query(CareerProfile).filter(CareerProfile.user_id == user.id).first()
        )
        if existing:
            db.delete(existing)
            db.commit()

        print("📝 Inserting Core Profile (with Awards)...")
        profile = CareerProfile(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=data.get("full_name", "Aaron T. Myers"),
            label=data.get("clearance"),
            email=DEFAULT_EMAIL,
            summary=f"Clearance: {data.get('clearance')}",
            skills=data.get("core_domains", []),
            # NEW: Awards Array
            awards=data.get("awards", []),
        )
        db.add(profile)

        # NEW: Insert Certifications
        print(f"   ↳ Importing {len(data.get('certifications', []))} certifications...")
        for cert_str in data.get("certifications", []):
            parsed = parse_cert_string(cert_str)
            cert = CareerCertification(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                name=parsed["name"],
                organization=parsed.get("organization"),
                date=parsed.get("date"),
            )
            db.add(cert)

        # Insert Work Experience
        print(
            f"   ↳ Importing {len(data.get('roles', []))} work roles with structured highlights..."
        )
        for role in data.get("roles", []):
            exp = CareerExperience(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                company=role.get("organization", ""),
                position=role.get("title", ""),
                start_date=role.get("start_date"),
                end_date=role.get("end_date"),
                summary=f"Location: {role.get('location')} | Seniority: {role.get('seniority')}",
            )
            db.add(exp)
            db.commit()  # Need exp ID

            # NEW: Structured Highlights
            for ach in role.get("achievements", []):
                hl = CareerExperienceHighlight(
                    id=str(uuid.uuid4()),
                    experience_id=exp.id,
                    description=ach.get("description", ""),
                    impact_metric=ach.get("impact_metric"),
                    domain_tags=ach.get("domain_tags", []),
                )
                db.add(hl)

        # Insert Education
        for edu_str in data.get("education", []):
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

        db.commit()
        print("✅ Profile Migration Successful!")

    except Exception as e:
        print(f"❌ Migration Failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    migrate_profile()
