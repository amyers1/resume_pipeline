import asyncio
import json
import logging
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from database import Base, engine, get_db
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from models import (
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerExperienceHighlight,
    CareerProfile,
    CareerProject,
    Job,
    JobListResponse,
    JobResponse,
    JobSubmitRequest,
    ProfileCreate,
    ProfileResponse,
    User,
    UserCreate,
    UserResponse,
)
from rabbitmq import RabbitMQClient, RabbitMQConfig, publish_job_request
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload
from sse_starlette.sse import EventSourceResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume Pipeline API")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://resume-pipeline.myerslab.me",
        "https://api.resume-pipeline.myerslab.me",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# SSE BROADCASTER
# ==========================


class SSEBroadcaster:
    def __init__(self):
        self.connections: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def connect(self):
        queue = asyncio.Queue()
        async with self._lock:
            self.connections.append(queue)
        return queue

    async def disconnect(self, queue):
        async with self._lock:
            if queue in self.connections:
                self.connections.remove(queue)

    async def broadcast(self, message: dict):
        disconnected = []
        async with self._lock:
            for queue in self.connections:
                try:
                    await queue.put(json.dumps(message))
                except Exception:
                    disconnected.append(queue)

            for q in disconnected:
                self.connections.remove(q)


broadcaster = SSEBroadcaster()


# Background RabbitMQ Consumer
def start_rabbitmq_consumer():
    """Runs in a separate thread to consume RabbitMQ messages."""
    global loop
    config = RabbitMQConfig()

    def on_message(channel, method, properties, body):
        try:
            data = json.loads(body)
            # Schedule the broadcast in the main event loop
            asyncio.run_coroutine_threadsafe(broadcaster.broadcast(data), loop)
        except Exception as e:
            logger.error(f"Broadcast error: {e}")

    try:
        client = RabbitMQClient(config)
        client.connect()
        client.channel.basic_consume(
            queue=config.status_queue, on_message_callback=on_message, auto_ack=True
        )
        client.channel.basic_consume(
            queue=config.progress_queue, on_message_callback=on_message, auto_ack=True
        )
        # Also listen for completion/errors
        # (Assuming your routing keys are set up to duplicate these to status_queue or similar)

        client.channel.start_consuming()
    except Exception as e:
        logger.error(f"RabbitMQ consumer failed: {e}")


@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()
    t = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    t.start()


# ==========================
# SYSTEM ENDPOINTS
# ==========================


@app.get("/health")
def health_check():
    """Health check endpoint for frontend and orchestration."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/events")
async def sse_events():
    """Unified SSE stream for all clients."""
    queue = await broadcaster.connect()

    async def event_generator():
        try:
            while True:
                msg = await queue.get()
                yield {"data": msg}
        except asyncio.CancelledError:
            await broadcaster.disconnect(queue)

    return EventSourceResponse(event_generator())


# ==========================
# USER ENDPOINTS
# ==========================


@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(email=user.email, full_name=user.full_name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


# ==========================
# PROFILE ENDPOINTS
# ==========================


@app.post("/users/{user_id}/profiles", response_model=ProfileResponse)
def create_profile(
    user_id: str, profile_req: ProfileCreate, db: Session = Depends(get_db)
):
    """Create profile with nested certs, awards, and structured highlights."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = profile_req.profile_json
    basics = data.get("basics", {})
    location = basics.get("location", {})

    # 1. Main Profile
    new_profile = CareerProfile(
        id=str(uuid.uuid4()),
        user_id=user_id,
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
        # Awards are now an array on the profile
        awards=data.get("awards", []),
    )
    db.add(new_profile)
    db.commit()

    # 2. Certifications (New Model)
    for cert in data.get("certifications", []):
        c = CareerCertification(
            id=str(uuid.uuid4()),
            profile_id=new_profile.id,
            name=cert.get("name") or cert,  # Handle both string and object
            organization=cert.get("issuer") if isinstance(cert, dict) else None,
            date=cert.get("date") if isinstance(cert, dict) else None,
        )
        db.add(c)

    # 3. Experience & Highlights (New Model)
    for work in data.get("work", []):
        exp = CareerExperience(
            id=str(uuid.uuid4()),
            profile_id=new_profile.id,
            company=work.get("name", ""),
            position=work.get("position", ""),
            start_date=work.get("startDate"),
            end_date=work.get("endDate"),
            summary=work.get("summary"),
        )
        db.add(exp)
        db.commit()  # Need exp.id

        # Add Highlights (Achievements)
        # Supports both simple strings (old format) and objects (new format)
        highlights = work.get("achievements") or work.get("highlights") or []
        for h in highlights:
            if isinstance(h, str):
                # Simple string mode
                hl = CareerExperienceHighlight(
                    id=str(uuid.uuid4()), experience_id=exp.id, description=h
                )
            else:
                # Structured mode
                hl = CareerExperienceHighlight(
                    id=str(uuid.uuid4()),
                    experience_id=exp.id,
                    description=h.get("description", ""),
                    impact_metric=h.get("impact_metric"),
                    domain_tags=h.get("domain_tags", []),
                )
            db.add(hl)

    # 4. Education
    for edu in data.get("education", []):
        ed = CareerEducation(
            id=str(uuid.uuid4()),
            profile_id=new_profile.id,
            institution=edu.get("institution", ""),
            area=edu.get("area"),
            study_type=edu.get("studyType"),
            start_date=edu.get("startDate"),
            end_date=edu.get("endDate"),
            score=edu.get("score"),
            courses=edu.get("courses", []),
        )
        db.add(ed)

    # 5. Projects
    for proj in data.get("projects", []):
        pr = CareerProject(
            id=str(uuid.uuid4()),
            profile_id=new_profile.id,
            name=proj.get("name", ""),
            description=proj.get("description"),
            url=proj.get("url"),
            keywords=proj.get("keywords", []),
        )
        db.add(pr)

    db.commit()
    db.refresh(new_profile)

    resp = ProfileResponse.from_orm(new_profile)
    resp.profile_json = new_profile.to_full_json()
    return resp


@app.get("/users/{user_id}/profiles", response_model=List[ProfileResponse])
def list_profiles(user_id: str, db: Session = Depends(get_db)):
    profiles = (
        db.query(CareerProfile)
        .options(
            joinedload(CareerProfile.experience).joinedload(
                CareerExperience.highlights
            ),
            joinedload(CareerProfile.education),
            joinedload(CareerProfile.certifications),
        )
        .filter(CareerProfile.user_id == user_id)
        .all()
    )

    results = []
    for p in profiles:
        r = ProfileResponse.from_orm(p)
        r.profile_json = p.to_full_json()
        results.append(r)
    return results


@app.get("/profiles")
def list_all_profiles(db: Session = Depends(get_db)):
    profiles = db.query(CareerProfile).all()
    results = []
    for p in profiles:
        r = ProfileResponse.from_orm(p)
        r.profile_json = p.to_full_json()
        results.append(r)
    return results


# ==========================
# JOB ENDPOINTS
# ==========================


@app.post("/jobs", response_model=JobResponse, status_code=201)
def submit_job(request: JobSubmitRequest, db: Session = Depends(get_db)):
    """Submit a new job, unpacking JSON into normalized columns."""
    job_id = str(uuid.uuid4())

    # 1. Resolve Profile
    final_profile_json = None
    if request.profile_id:
        profile_record = (
            db.query(CareerProfile)
            .filter(CareerProfile.id == request.profile_id)
            .first()
        )
        if not profile_record:
            raise HTTPException(status_code=404, detail="Profile ID not found")
        final_profile_json = profile_record.to_full_json()
        if not request.user_id:
            request.user_id = profile_record.user_id
    elif request.career_profile_data:
        final_profile_json = request.career_profile_data
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either profile_id or career_profile_data",
        )

    # 2. Unpack JSON Schema
    data = request.job_data
    jd = data.get("job_details", {})
    ben = data.get("benefits", {})
    desc = data.get("job_description", {})
    ctx = jd.get("job_board_list_context", {})

    def safe_int(val):
        try:
            return int(val) if val is not None else None
        except:
            return None

    new_job = Job(
        id=job_id,
        user_id=request.user_id,
        # --- JOB DETAILS ---
        company=jd.get("company", "Unknown"),
        job_title=jd.get("job_title", "Unknown"),
        source=jd.get("source"),
        platform=jd.get("platform"),
        company_rating=jd.get("company_rating"),
        location=jd.get("location"),
        location_detail=jd.get("location_detail"),
        employment_type=jd.get("employment_type"),
        pay_currency=jd.get("pay_currency", "USD"),
        pay_min_annual=safe_int(jd.get("pay_min_annual")),
        pay_max_annual=safe_int(jd.get("pay_max_annual")),
        pay_rate_type=jd.get("pay_rate_type"),
        pay_display=jd.get("pay_display"),
        remote_type=jd.get("remote_type"),
        work_model=jd.get("work_model"),
        work_model_notes=jd.get("work_model_notes"),
        job_post_url=jd.get("job_post_url"),
        apply_url=jd.get("apply_url"),
        posting_age=jd.get("posting_age"),
        security_clearance_required=jd.get("security_clearance_required"),
        security_clearance_preferred=jd.get("security_clearance_preferred"),
        # Search Context
        search_keywords=ctx.get("search_keywords"),
        search_location=ctx.get("search_location"),
        search_radius=safe_int(ctx.get("search_radius_miles")),
        # --- BENEFITS ---
        benefits_listed=ben.get("listed_benefits", []),
        benefits_text=ben.get("benefits_text"),
        benefits_eligibility=ben.get("eligibility_notes"),
        benefits_relocation=ben.get("relocation"),
        benefits_sign_on_bonus=ben.get("sign_on_bonus"),
        # --- DESCRIPTION ---
        jd_headline=desc.get("headline"),
        jd_short_summary=desc.get("short_summary"),
        jd_full_text=desc.get("full_text"),
        jd_experience_min=safe_int(desc.get("required_experience_years_min")),
        jd_education=desc.get("required_education"),
        jd_must_have_skills=desc.get("must_have_skills", []),
        jd_nice_to_have_skills=desc.get("nice_to_have_skills", []),
        # --- CONFIG ---
        career_profile_json=final_profile_json,
        template=request.template,
        output_backend=request.output_backend,
        priority=request.priority,
        advanced_settings=request.advanced_settings.dict()
        if request.advanced_settings
        else {},
        status="queued",
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # 3. Publish to RabbitMQ
    publish_job_request(
        job_id=job_id,
        job_json_path="DB",
        career_profile_path="DB",
        template=request.template,
        output_backend=request.output_backend,
        priority=request.priority,
    )

    # We manually attach the reconstructed JSON for the response
    # (Since we removed the JSON column from DB, but Frontend expects it)
    response_obj = JobResponse.from_orm(new_job)
    response_obj.job_description_json = new_job.to_schema_json()

    return response_obj


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Hydrate the JSON field for frontend compatibility
    resp = JobResponse.from_orm(job)
    resp.job_description_json = job.to_schema_json()
    return resp


@app.get("/jobs", response_model=JobListResponse)
def list_jobs(page: int = 1, size: int = 20, db: Session = Depends(get_db)):
    skip = (page - 1) * size
    total = db.query(Job).count()
    jobs = db.query(Job).order_by(desc(Job.created_at)).offset(skip).limit(size).all()

    # Hydrate list items
    items = []
    for j in jobs:
        r = JobResponse.from_orm(j)
        r.job_description_json = j.to_schema_json()
        items.append(r)

    return {"items": items, "total": total, "page": page, "size": size}


@app.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """
    Deletes a job from the database and removes its generated artifacts from disk.
    """
    # 1. Find the job in the database
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # 2. Delete the record from the database
    db.delete(job)
    db.commit()

    # 3. Clean up the file system (Output Directory)
    job_dir = OUTPUT_DIR / job_id
    if job_dir.exists() and job_dir.is_dir():
        try:
            shutil.rmtree(job_dir)
        except Exception as e:
            logger.error(f"Failed to delete directory {job_dir}: {e}")

    return None


# ==========================
# FILE ENDPOINTS
# ==========================


@app.get("/jobs/{job_id}/files")
def list_job_files(job_id: str):
    """List generated files for a specific job."""
    job_dir = OUTPUT_DIR / job_id
    if not job_dir.exists():
        return []

    files = []
    for f in job_dir.glob("*"):
        if f.is_file():
            files.append(
                {
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime),
                }
            )
    return files


@app.get("/jobs/{job_id}/files/{filename}")
def download_job_file(job_id: str, filename: str):
    """Download a specific artifact."""
    file_path = OUTPUT_DIR / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path, filename=filename, media_type="application/octet-stream"
    )


# ==========================
# TEMPLATE ENDPOINTS
# ==========================


@app.get("/job-templates")
def list_job_templates():
    """List available resume templates."""
    # This matches the structure expected by the frontend
    return [
        {"name": "Awesome CV", "filename": "awesome-cv", "type": "latex"},
        {"name": "Modern Deedy", "filename": "modern-deedy", "type": "latex"},
        {"name": "Standard HTML", "filename": "resume.html.j2", "type": "html"},
    ]
