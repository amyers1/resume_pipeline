#!/usr/bin/env python3
"""
Script to reinitialize career profile tables and import legacy career_profile.json

This script:
1. Drops and recreates career profile related tables
2. Ensures a user exists for the profile
3. Converts legacy JSON format to new database schema
4. Imports all data with proper relationships

Usage:
    python import_legacy_profile.py <path_to_legacy_career_profile.json>
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add backend to path if running from different directory
sys.path.insert(0, str(Path(__file__).parent))

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
from sqlalchemy import text


def drop_career_tables(session):
    """Drop all career profile related tables in correct order (respecting foreign keys)."""
    print("🗑️  Dropping existing career profile tables...")

    tables_to_drop = [
        "career_experience_highlights",
        "career_certifications",
        "career_projects",
        "career_education",
        "career_experience",
        "career_profiles",
    ]

    for table in tables_to_drop:
        try:
            session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            print(f"  ✓ Dropped {table}")
        except Exception as e:
            print(f"  ⚠️  Could not drop {table}: {e}")

    session.commit()
    print("✅ Tables dropped successfully\n")


def create_career_tables():
    """Recreate career profile tables using SQLAlchemy models."""
    print("🔨 Creating career profile tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully\n")


def ensure_user_exists(session, email, full_name):
    """Ensure a user exists for the profile."""
    print(f"👤 Checking for user: {email}")

    user = session.query(User).filter(User.email == email).first()

    if not user:
        print(f"  Creating new user: {full_name}")
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            full_name=full_name,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"  ✓ User created: {user.id}")
    else:
        print(f"  ✓ User exists: {user.id}")

    return user


def parse_date_range(role):
    """Parse start/end dates from role data."""
    start_date = role.get("start_date")
    end_date = role.get("end_date")

    # Convert YYYY-MM format to proper date strings if needed
    if start_date and len(start_date) == 7:  # YYYY-MM
        start_date = f"{start_date}-01"
    if end_date and len(end_date) == 7:  # YYYY-MM
        end_date = f"{end_date}-01"

    return start_date, end_date


def convert_legacy_to_profile(legacy_data, user_id):
    """Convert legacy career_profile.json format to database models."""
    print("🔄 Converting legacy format to database schema...")

    # Extract basic information
    full_name = legacy_data.get("full_name", "Unknown")
    clearance = legacy_data.get("clearance", "")
    core_domains = legacy_data.get("core_domains", [])

    # Create profile summary from clearance
    summary = f"Cleared: {clearance}" if clearance else None

    print(f"  Profile: {full_name}")
    print(f"  Domains: {len(core_domains)} core domains")
    print(f"  Roles: {len(legacy_data.get('roles', []))} positions")
    print(f"  Education: {len(legacy_data.get('education', []))} entries")
    print(f"  Certifications: {len(legacy_data.get('certifications', []))} entries")
    print(f"  Awards: {len(legacy_data.get('awards', []))} entries")

    # Create the profile
    profile = CareerProfile(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=full_name,
        label="Technical Leader and Systems Engineer",  # Can be customized
        email="aaron.t.myers@gmail.com",  # Not in legacy format
        phone="405-249-2897",  # Not in legacy format
        url=None,  # Not in legacy format
        summary=summary,
        city="OKC Metro",  # Not in legacy format
        region="OK",  # Not in legacy format
        country_code="US",  # Default
        skills=core_domains,
        languages=[],
        awards=legacy_data.get("awards", []),
    )

    return profile, legacy_data


def import_work_experience(session, profile_id, roles):
    """Import work experience and achievements."""
    print(f"\n💼 Importing {len(roles)} work experiences...")

    for idx, role in enumerate(roles, 1):
        title = role.get("title", "Unknown Position")
        org = role.get("organization", "Unknown Organization")
        location = role.get("location", "")
        seniority = role.get("seniority", "")

        start_date, end_date = parse_date_range(role)

        # Create summary from location and seniority
        summary_parts = [p for p in [location, seniority] if p]
        summary = " | ".join(summary_parts) if summary_parts else None

        print(f"  {idx}. {title} at {org}")

        # Create experience record
        exp = CareerExperience(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            company=org,
            position=title,
            start_date=start_date,
            end_date=end_date,
            is_current=(end_date is None or end_date == ""),
            summary=summary,
        )
        session.add(exp)
        session.flush()  # Get the ID

        # Add achievements as highlights
        achievements = role.get("achievements", [])
        print(f"     Adding {len(achievements)} achievements...")

        for ach in achievements:
            highlight = CareerExperienceHighlight(
                id=str(uuid.uuid4()),
                experience_id=exp.id,
                description=ach.get("description", ""),
                impact_metric=ach.get("impact_metric"),
                domain_tags=ach.get("domain_tags", []),
            )
            session.add(highlight)

    print(f"  ✅ Imported {len(roles)} work experiences")


def import_education(session, profile_id, education_list):
    """Import education records."""
    if not education_list:
        return

    print(f"\n🎓 Importing {len(education_list)} education entries...")

    for idx, edu_str in enumerate(education_list, 1):
        # Parse education string format:
        # "M.S., Electrical Engineering – Air Force Institute of Technology, WPAFB, OH (2013)"
        # "B.S., Electrical Engineering – University of Oklahoma, Norman, OK (2005)"

        try:
            # Split by '–' to separate degree from institution
            parts = edu_str.split("–")

            if len(parts) >= 2:
                degree_part = parts[0].strip()
                school_part = parts[1].strip()

                # Extract degree type and area
                degree_split = degree_part.split(",", 1)
                study_type = degree_split[0].strip() if degree_split else ""
                area = degree_split[1].strip() if len(degree_split) > 1 else ""

                # Extract year from parentheses
                import re

                year_match = re.search(r"\((\d{4})\)", school_part)
                end_date = year_match.group(1) if year_match else None

                # Institution is everything before the year
                institution = re.sub(r"\s*\(\d{4}\)\s*$", "", school_part).strip()

                print(f"  {idx}. {study_type} - {institution} ({end_date})")

                edu = CareerEducation(
                    id=str(uuid.uuid4()),
                    profile_id=profile_id,
                    institution=institution,
                    area=area,
                    study_type=study_type,
                    start_date=None,
                    end_date=end_date,
                    score=None,
                    courses=[],
                )
                session.add(edu)
            else:
                # Fallback for non-standard format
                print(f"  {idx}. {edu_str} (non-standard format)")
                edu = CareerEducation(
                    id=str(uuid.uuid4()),
                    profile_id=profile_id,
                    institution=edu_str,
                    area=None,
                    study_type=None,
                    start_date=None,
                    end_date=None,
                    score=None,
                    courses=[],
                )
                session.add(edu)
        except Exception as e:
            print(f"  ⚠️  Error parsing education entry: {edu_str}")
            print(f"     {e}")

    print(f"  ✅ Imported {len(education_list)} education entries")


def import_certifications(session, profile_id, cert_list):
    """Import certifications."""
    if not cert_list:
        return

    print(f"\n📜 Importing {len(cert_list)} certifications...")

    for idx, cert_str in enumerate(cert_list, 1):
        # Parse certification string format:
        # "Project Management Professional (PMP), Project Management Institute (2025)"
        # "Engineering and Technical Management Practitioner, DAWIA (2022)"

        try:
            import re

            # Extract year from end
            year_match = re.search(r"\((\d{4})\)\s*$", cert_str)
            date = year_match.group(1) if year_match else None

            # Remove year to get name and organization
            cert_without_year = re.sub(r"\s*\(\d{4}\)\s*$", "", cert_str).strip()

            # Split by comma to separate name from organization
            parts = cert_without_year.split(",")

            name = parts[0].strip()
            organization = parts[1].strip() if len(parts) > 1 else None

            print(f"  {idx}. {name} - {organization} ({date})")

            cert = CareerCertification(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                name=name,
                organization=organization,
                date=date,
            )
            session.add(cert)
        except Exception as e:
            print(f"  ⚠️  Error parsing certification: {cert_str}")
            print(f"     {e}")

    print(f"  ✅ Imported {len(cert_list)} certifications")


def main():
    """Main import process."""
    if len(sys.argv) < 2:
        print("Usage: python import_legacy_profile.py <path_to_career_profile.json>")
        sys.exit(1)

    profile_path = Path(sys.argv[1])

    if not profile_path.exists():
        print(f"❌ Error: File not found: {profile_path}")
        sys.exit(1)

    print("=" * 70)
    print("LEGACY CAREER PROFILE IMPORTER")
    print("=" * 70)
    print(f"📂 Input file: {profile_path}")
    print()

    # Load legacy data
    print("📖 Loading legacy career profile...")
    with open(profile_path, "r", encoding="utf-8") as f:
        legacy_data = json.load(f)
    print("✅ Legacy data loaded\n")

    # Database session
    session = SessionLocal()

    try:
        # Step 1: Drop existing tables
        drop_career_tables(session)

        # Step 2: Recreate tables
        create_career_tables()

        # Step 3: Ensure user exists
        email = "aaron.t.myers@gmail.com"  # Default email
        full_name = legacy_data.get("full_name", "Aaron T. Myers")
        user = ensure_user_exists(session, email, full_name)

        # Step 4: Convert and create profile
        profile, legacy_data = convert_legacy_to_profile(legacy_data, user.id)
        session.add(profile)
        session.flush()  # Get profile ID
        print(f"✅ Profile created: {profile.id}\n")

        # Step 5: Import work experience
        import_work_experience(session, profile.id, legacy_data.get("roles", []))

        # Step 6: Import education
        import_education(session, profile.id, legacy_data.get("education", []))

        # Step 7: Import certifications
        import_certifications(
            session, profile.id, legacy_data.get("certifications", [])
        )

        # Commit all changes
        session.commit()

        print("\n" + "=" * 70)
        print("✅ IMPORT COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"Profile ID: {profile.id}")
        print(f"User ID: {user.id}")
        print(f"User Email: {user.email}")
        print()
        print("You can now:")
        print("  1. View the profile in the web UI at /profiles")
        print("  2. Use it in resume generation")
        print("  3. Edit it through the profile editor")
        print()

    except Exception as e:
        session.rollback()
        print("\n" + "=" * 70)
        print("❌ IMPORT FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
