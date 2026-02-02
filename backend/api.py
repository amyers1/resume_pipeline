import asyncio
import io
import json
import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aioboto3
from database import Base, engine, get_db
from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from models import (
    CareerCertification,
    CareerEducation,
    CareerExperience,
    CareerExperienceHighlight,
    CareerProfile,
    CareerProject,
    CritiqueResponse,
    JDRequirementsSummary,
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

# Ensure rabbitmq.py exports these from the previous refactor
from rabbitmq import AsyncRabbitMQClient, RabbitMQConfig, publish_job_request
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==========================
# ASYNC S3 CLIENT
# ==========================
class AsyncS3Manager:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint = os.getenv("S3_ENDPOINT")
        self.access_key = os.getenv("S3_ACCESS_KEY")
        self.secret_key = os.getenv("S3_SECRET_KEY")
        self.bucket = os.getenv("S3_BUCKET", "resume-pipeline")
        self.enabled = os.getenv("ENABLE_S3", "false").lower() == "true"

    def client(self):
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=True,  # Set to False if using local Minio without SSL
        )


s3_manager = AsyncS3Manager()

app = FastAPI(title="Resume Pipeline API")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# ==========================
# BACKGROUND TASKS
# ==========================


async def run_async_consumer():
    """Background task to consume RabbitMQ messages (Status & Progress only)."""
    config = RabbitMQConfig()
    client = AsyncRabbitMQClient(config)

    try:
        await client.connect()
        logger.info("✅ API Worker connected to RabbitMQ (listening for updates)")

        # 1. Declare queues to ensure they exist
        queue = await client.channel.declare_queue(config.status_queue, durable=True)
        progress_queue = await client.channel.declare_queue(
            config.progress_queue, durable=True
        )

        # 2. Define the consumption logic
        async def process_queue(q, name):
            logger.info(f"🎧 Listening to queue: {name}")
            async with q.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            data = json.loads(message.body.decode())
                            await broadcaster.broadcast(data)
                        except Exception as e:
                            logger.error(f"Broadcast error on {name}: {e}")

        # 3. Run both consumers concurrently
        await asyncio.gather(
            process_queue(queue, "status"), process_queue(progress_queue, "progress")
        )

    except asyncio.CancelledError:
        logger.info("RabbitMQ consumer cancelled")
        await client.close()
    except Exception as e:
        logger.error(f"RabbitMQ consumer failed: {e}")


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_async_consumer())


# ==========================
# SYSTEM ENDPOINTS
# ==========================


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/events")
async def sse_events():
    queue = await broadcaster.connect()

    async def event_generator():
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {"data": msg}
                except asyncio.TimeoutError:
                    yield {"comment": "keep-alive"}
        except asyncio.CancelledError:
            await broadcaster.disconnect(queue)

    return EventSourceResponse(event_generator())


# ==========================
# USER ENDPOINTS
# ==========================


@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))
    db_user = result.scalars().first()

    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(email=user.email, full_name=user.full_name)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.get("/users", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()


# ==========================
# PROFILE ENDPOINTS
# ==========================


@app.post("/users/{user_id}/profiles", response_model=ProfileResponse)
async def create_profile(
    user_id: str, profile_req: ProfileCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = profile_req.profile_json
    basics = data.get("basics", {})
    location = basics.get("location", {})

    new_profile = CareerProfile(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=basics.get("name", "Unknown"),
        label=basics.get("label"),
        email=basics.get("email"),
        phone=basics.get("phone"),
        url=basics.get("url"),
        linkedin=basics.get("linkedin"),
        clearance=basics.get("clearance"),
        summary=basics.get("summary"),
        city=location.get("city"),
        region=location.get("region"),
        country_code=location.get("countryCode"),
        skills=[s.get("name") for s in data.get("skills", []) if s.get("name")],
        core_domains=data.get("core_domains", []),
        awards=data.get("awards", []),
        biography=data.get("biography"),
    )
    db.add(new_profile)
    await db.flush()

    for cert in data.get("certifications", []):
        c = CareerCertification(
            id=str(uuid.uuid4()),
            profile_id=new_profile.id,
            name=cert.get("name") or cert,
            organization=cert.get("issuer") if isinstance(cert, dict) else None,
            date=cert.get("date") if isinstance(cert, dict) else None,
        )
        db.add(c)

    for work in data.get("work", []):
        exp = CareerExperience(
            id=str(uuid.uuid4()),
            profile_id=new_profile.id,
            company=work.get("name", ""),
            position=work.get("position", ""),
            start_date=work.get("startDate"),
            end_date=work.get("endDate"),
            location=work.get("location"),
            seniority=work.get("seniority"),
            summary=work.get("summary"),
        )
        db.add(exp)
        await db.flush()

        highlights = work.get("achievements") or work.get("highlights") or []
        for h in highlights:
            if isinstance(h, str):
                hl = CareerExperienceHighlight(
                    id=str(uuid.uuid4()), experience_id=exp.id, description=h
                )
            else:
                hl = CareerExperienceHighlight(
                    id=str(uuid.uuid4()),
                    experience_id=exp.id,
                    description=h.get("description", ""),
                    impact_metric=h.get("impact_metric"),
                    domain_tags=h.get("domain_tags", []),
                    skills=h.get("skills", []),
                )
            db.add(hl)

    for edu in data.get("education", []):
        ed = CareerEducation(
            id=str(uuid.uuid4()),
            profile_id=new_profile.id,
            institution=edu.get("institution", ""),
            area=edu.get("area"),
            study_type=edu.get("studyType"),
            start_date=edu.get("startDate"),
            end_date=edu.get("endDate"),
            location=edu.get("location"),
            score=edu.get("score"),
            courses=edu.get("courses", []),
        )
        db.add(ed)

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

    await db.commit()
    await db.refresh(new_profile)

    resp = ProfileResponse.model_validate(new_profile, from_attributes=True)
    resp.profile_json = new_profile.to_full_json()
    return resp


@app.get("/users/{user_id}/profiles", response_model=List[ProfileResponse])
async def list_user_profiles(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="User not found")

    stmt = (
        select(CareerProfile)
        .where(CareerProfile.user_id == user_id)
        .order_by(desc(CareerProfile.updated_at))
        .options(
            selectinload(CareerProfile.experience).selectinload(
                CareerExperience.highlights
            ),
            selectinload(CareerProfile.education),
            selectinload(CareerProfile.projects),
            selectinload(CareerProfile.certifications),
        )
    )
    result = await db.execute(stmt)
    profiles = result.scalars().all()

    results = []
    for p in profiles:
        result = ProfileResponse(
            id=p.id,
            name=p.name,
            user_id=p.user_id,
            created_at=p.created_at,
            updated_at=p.updated_at,
            profile_json=p.to_full_json(),
        )
        results.append(result)
    return results


@app.get("/users/{user_id}/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    user_id: str, profile_id: str, db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(CareerProfile)
        .where(CareerProfile.id == profile_id, CareerProfile.user_id == user_id)
        .options(
            selectinload(CareerProfile.experience).selectinload(
                CareerExperience.highlights
            ),
            selectinload(CareerProfile.education),
            selectinload(CareerProfile.projects),
            selectinload(CareerProfile.certifications),
        )
    )
    result = await db.execute(stmt)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        user_id=profile.user_id,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        profile_json=profile.to_full_json(),
    )


@app.put("/users/{user_id}/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    user_id: str,
    profile_id: str,
    profile_req: ProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CareerProfile).where(
        CareerProfile.id == profile_id, CareerProfile.user_id == user_id
    )
    result = await db.execute(stmt)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    data = profile_req.profile_json
    basics = data.get("basics", {})
    location = basics.get("location", {})

    # Update basic profile fields
    profile.name = basics.get("name", profile.name)
    profile.label = basics.get("label")
    profile.email = basics.get("email")
    profile.phone = basics.get("phone")
    profile.url = basics.get("url")
    profile.linkedin = basics.get("linkedin")
    profile.clearance = basics.get("clearance")
    profile.summary = basics.get("summary")
    profile.city = location.get("city")
    profile.region = location.get("region")
    profile.country_code = location.get("countryCode")
    profile.skills = [s.get("name") for s in data.get("skills", []) if s.get("name")]
    profile.core_domains = data.get("core_domains", [])
    profile.awards = [
        a.get("title") if isinstance(a, dict) else a for a in data.get("awards", [])
    ]
    profile.biography = data.get("biography")
    profile.updated_at = datetime.utcnow()

    # FIX: Delete child records (Highlights) explicitly first to prevent FK violation
    # 1. Fetch experience IDs to clean up highlights
    result_exp = await db.execute(
        select(CareerExperience.id).where(CareerExperience.profile_id == profile_id)
    )
    exp_ids = result_exp.scalars().all()

    # 2. Delete Highlights (Leaf nodes)
    if exp_ids:
        await db.execute(
            delete(CareerExperienceHighlight).where(
                CareerExperienceHighlight.experience_id.in_(exp_ids)
            )
        )

    # 3. Delete Parents (Experience, Education, etc.)
    await db.execute(
        delete(CareerExperience).where(CareerExperience.profile_id == profile_id)
    )
    await db.execute(
        delete(CareerEducation).where(CareerEducation.profile_id == profile_id)
    )
    await db.execute(
        delete(CareerProject).where(CareerProject.profile_id == profile_id)
    )
    await db.execute(
        delete(CareerCertification).where(CareerCertification.profile_id == profile_id)
    )

    await db.flush()

    # Re-create Data (Same logic as create)
    for work in data.get("work", []):
        exp = CareerExperience(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            company=work.get("name", "Unknown"),
            position=work.get("position", "Unknown"),
            start_date=work.get("startDate"),
            end_date=work.get("endDate"),
            is_current=not work.get("endDate"),
            location=work.get("location"),
            seniority=work.get("seniority"),
            summary=work.get("summary"),
        )
        db.add(exp)
        await db.flush()

        highlights = work.get("achievements") or work.get("highlights") or []
        for hl in highlights:
            if isinstance(hl, str):
                highlight = CareerExperienceHighlight(
                    id=str(uuid.uuid4()), experience_id=exp.id, description=hl
                )
                db.add(highlight)
            elif isinstance(hl, dict):
                highlight = CareerExperienceHighlight(
                    id=str(uuid.uuid4()),
                    experience_id=exp.id,
                    description=hl.get("description", ""),
                    impact_metric=hl.get("impact_metric"),
                    domain_tags=hl.get("domain_tags", []),
                    skills=hl.get("skills", []),
                )
                db.add(highlight)

    for edu in data.get("education", []):
        education = CareerEducation(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            institution=edu.get("institution", "Unknown"),
            area=edu.get("area"),
            study_type=edu.get("studyType"),
            start_date=edu.get("startDate"),
            end_date=edu.get("endDate"),
            location=edu.get("location"),
            score=edu.get("score"),
            courses=edu.get("courses", []),
        )
        db.add(education)

    for proj in data.get("projects", []):
        project = CareerProject(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            name=proj.get("name", "Unknown"),
            description=proj.get("description"),
            url=proj.get("url"),
            keywords=proj.get("keywords", []),
            roles=proj.get("roles", []),
            start_date=proj.get("startDate"),
            end_date=proj.get("endDate"),
        )
        db.add(project)

    for cert in data.get("certifications", []):
        certification = CareerCertification(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            name=cert.get("name", "Unknown"),
            date=cert.get("date"),
            organization=cert.get("issuer"),
        )
        db.add(certification)

    await db.commit()

    # Re-fetch for clean response
    stmt = (
        select(CareerProfile)
        .where(CareerProfile.id == profile_id)
        .options(
            selectinload(CareerProfile.experience).selectinload(
                CareerExperience.highlights
            ),
            selectinload(CareerProfile.education),
            selectinload(CareerProfile.projects),
            selectinload(CareerProfile.certifications),
        )
    )
    result = await db.execute(stmt)
    refreshed_profile = result.scalars().first()

    return ProfileResponse(
        id=refreshed_profile.id,
        name=refreshed_profile.name,
        user_id=refreshed_profile.user_id,
        created_at=refreshed_profile.created_at,
        updated_at=refreshed_profile.updated_at,
        profile_json=refreshed_profile.to_full_json(),
    )


@app.delete("/users/{user_id}/profiles/{profile_id}")
async def delete_profile(
    user_id: str, profile_id: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CareerProfile).where(
            CareerProfile.id == profile_id, CareerProfile.user_id == user_id
        )
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await db.delete(profile)
    await db.commit()
    return {"message": "Profile deleted successfully"}


@app.get("/profiles")
async def list_all_profiles(db: AsyncSession = Depends(get_db)):
    stmt = select(CareerProfile).options(
        selectinload(CareerProfile.experience).selectinload(
            CareerExperience.highlights
        ),
        selectinload(CareerProfile.education),
        selectinload(CareerProfile.projects),
        selectinload(CareerProfile.certifications),
    )
    result = await db.execute(stmt)
    profiles = result.scalars().all()

    results = []
    for p in profiles:
        r = ProfileResponse.model_validate(p, from_attributes=True)
        r.profile_json = p.to_full_json()
        results.append(r)
    return results


# ==========================
# JOB ENDPOINTS
# ==========================


@app.post("/jobs", response_model=JobResponse, status_code=201)
async def submit_job(request: JobSubmitRequest, db: AsyncSession = Depends(get_db)):
    job_id = str(uuid.uuid4())
    final_profile_json = None

    if request.profile_id:
        result = await db.execute(
            select(CareerProfile)
            .where(CareerProfile.id == request.profile_id)
            .options(
                selectinload(CareerProfile.experience).selectinload(
                    CareerExperience.highlights
                ),
                selectinload(CareerProfile.education),
                selectinload(CareerProfile.projects),
                selectinload(CareerProfile.certifications),
            )
        )
        profile_record = result.scalars().first()
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

    data = request.job_data
    jd = data.get("job_details", {})
    ben = data.get("benefits", {})
    desc_ = data.get("job_description", {})
    ctx = jd.get("job_board_list_context", {})

    def safe_int(val):
        try:
            return int(val) if val is not None else None
        except:
            return None

    new_job = Job(
        id=job_id,
        user_id=request.user_id,
        root_job_id=job_id,
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
        search_keywords=ctx.get("search_keywords"),
        search_location=ctx.get("search_location"),
        search_radius=safe_int(ctx.get("search_radius_miles")),
        benefits_listed=ben.get("listed_benefits", []),
        benefits_text=ben.get("benefits_text"),
        benefits_eligibility=ben.get("eligibility_notes"),
        benefits_relocation=ben.get("relocation"),
        benefits_sign_on_bonus=ben.get("sign_on_bonus"),
        jd_headline=desc_.get("headline"),
        jd_short_summary=desc_.get("short_summary"),
        jd_full_text=desc_.get("full_text"),
        jd_experience_min=safe_int(desc_.get("required_experience_years_min")),
        jd_education=desc_.get("required_education"),
        jd_must_have_skills=desc_.get("must_have_skills", []),
        jd_nice_to_have_skills=desc_.get("nice_to_have_skills", []),
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
    await db.commit()
    await db.refresh(new_job)

    await publish_job_request(
        job_id=job_id,
        job_json_path="DB",
        career_profile_path="DB",
        template=request.template,
        output_backend=request.output_backend,
        priority=request.priority,
    )

    response_obj = JobResponse.model_validate(new_job, from_attributes=True)
    response_obj.job_description_json = new_job.to_schema_json()
    return response_obj


@app.post("/jobs/{job_id}/submit", response_model=JobResponse, status_code=201)
async def resubmit_job(
    job_id: str, options: dict = Body(default={}), db: AsyncSession = Depends(get_db)
):
    logger.info(f"🔄 Resubmitting job {job_id} with options: {options}")

    result = await db.execute(select(Job).where(Job.id == job_id))
    original_job = result.scalars().first()
    if not original_job:
        raise HTTPException(status_code=404, detail="Original job not found")

    new_job_id = str(uuid.uuid4())
    root_id = original_job.root_job_id if original_job.root_job_id else original_job.id

    new_template = options.get("template", original_job.template)

    new_backend = (
        options.get("output_backend")
        or options.get("outputBackend")
        or original_job.output_backend
    )

    new_priority = options.get("priority", original_job.priority)

    orig_settings = original_job.advanced_settings or {}
    new_settings = options.get("advanced_settings", {})
    final_settings = {**orig_settings, **new_settings}

    new_job = Job(
        id=new_job_id,
        user_id=original_job.user_id,
        root_job_id=root_id,
        company=original_job.company,
        job_title=original_job.job_title,
        source=original_job.source,
        platform=original_job.platform,
        company_rating=original_job.company_rating,
        location=original_job.location,
        location_detail=original_job.location_detail,
        employment_type=original_job.employment_type,
        pay_currency=original_job.pay_currency,
        pay_min_annual=original_job.pay_min_annual,
        pay_max_annual=original_job.pay_max_annual,
        pay_rate_type=original_job.pay_rate_type,
        pay_display=original_job.pay_display,
        remote_type=original_job.remote_type,
        work_model=original_job.work_model,
        work_model_notes=original_job.work_model_notes,
        job_post_url=original_job.job_post_url,
        apply_url=original_job.apply_url,
        posting_age=original_job.posting_age,
        security_clearance_required=original_job.security_clearance_required,
        security_clearance_preferred=original_job.security_clearance_preferred,
        search_keywords=original_job.search_keywords,
        search_location=original_job.search_location,
        search_radius=original_job.search_radius,
        benefits_listed=original_job.benefits_listed,
        benefits_text=original_job.benefits_text,
        benefits_eligibility=original_job.benefits_eligibility,
        benefits_relocation=original_job.benefits_relocation,
        benefits_sign_on_bonus=original_job.benefits_sign_on_bonus,
        jd_headline=original_job.jd_headline,
        jd_short_summary=original_job.jd_short_summary,
        jd_full_text=original_job.jd_full_text,
        jd_experience_min=original_job.jd_experience_min,
        jd_education=original_job.jd_education,
        jd_must_have_skills=original_job.jd_must_have_skills,
        jd_nice_to_have_skills=original_job.jd_nice_to_have_skills,
        career_profile_json=original_job.career_profile_json,
        critique_json=original_job.critique_json,
        template=new_template,
        output_backend=new_backend,
        priority=new_priority,
        advanced_settings=final_settings,
        status="queued",
    )

    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    try:
        logger.info(f"📤 Publishing resubmit request for job {new_job_id}...")
        await publish_job_request(
            job_id=new_job_id,
            job_json_path="DB",
            career_profile_path="DB",
            template=new_template,
            output_backend=new_backend,
            priority=new_priority,
        )
        logger.info(f"✅ Successfully queued job {new_job_id}")
    except Exception as e:
        logger.error(f"❌ Failed to publish job {new_job_id} to RabbitMQ: {e}")
        new_job.status = "failed"
        new_job.error_message = f"Failed to queue job: {str(e)}"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")

    response_obj = JobResponse.model_validate(new_job, from_attributes=True)
    response_obj.job_description_json = new_job.to_schema_json()
    return response_obj


@app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    history_items = []
    if job.root_job_id:
        h_result = await db.execute(
            select(Job)
            .where(Job.root_job_id == job.root_job_id)
            .order_by(desc(Job.created_at))
        )
        history_items = h_result.scalars().all()

    resp = JobResponse.model_validate(job, from_attributes=True)
    resp.job_description_json = job.to_schema_json()
    resp.history = history_items

    # Populate critique and jd_requirements from stored critique_json
    if job.critique_json:
        critique_data = job.critique_json
        # Extract the last critique from all_critiques for detailed info
        all_critiques = critique_data.get("all_critiques", [])
        last_critique = all_critiques[-1] if all_critiques else {}

        resp.critique = CritiqueResponse(
            score=critique_data.get("final_score"),
            ats_ok=critique_data.get("final_ats_ok"),
            length_ok=critique_data.get("final_length_ok"),
            jd_keyword_coverage=critique_data.get("final_keyword_coverage"),
            domain_match_coverage=critique_data.get("final_domain_coverage"),
            strengths=last_critique.get("strengths", []),
            weaknesses=last_critique.get("weaknesses", []),
            suggestions=last_critique.get("suggestions", []),
        )

        # Extract jd_requirements if available
        jd_req = critique_data.get("jd_requirements", {})
        if jd_req:
            resp.jd_requirements = JDRequirementsSummary(
                domain_focus=jd_req.get("domain_focus", []),
                must_have_skills=jd_req.get("must_have_skills", []),
                nice_to_have_skills=jd_req.get("nice_to_have_skills", []),
            )

    return resp


@app.get("/jobs", response_model=JobListResponse)
async def list_jobs(page: int = 1, size: int = 20, db: AsyncSession = Depends(get_db)):
    skip = (page - 1) * size

    latest_jobs_sub = (
        select(Job.root_job_id, func.max(Job.created_at).label("max_created_at"))
        .group_by(Job.root_job_id)
        .subquery()
    )

    count_stmt = select(func.count()).select_from(latest_jobs_sub)
    count_res = await db.execute(count_stmt)
    total = count_res.scalar() or 0

    stmt = (
        select(Job)
        .join(
            latest_jobs_sub,
            (Job.root_job_id == latest_jobs_sub.c.root_job_id)
            & (Job.created_at == latest_jobs_sub.c.max_created_at),
        )
        .order_by(desc(Job.created_at))
        .offset(skip)
        .limit(size)
    )

    jobs_res = await db.execute(stmt)
    jobs = jobs_res.scalars().all()

    items = []
    for j in jobs:
        r = JobResponse.model_validate(j, from_attributes=True)
        r.job_description_json = j.to_schema_json()
        r.template = j.template
        r.output_backend = j.output_backend
        items.append(r)

    return {"items": items, "total": total, "page": page, "size": size}


@app.delete("/jobs", status_code=200)
async def delete_all_jobs(db: AsyncSession = Depends(get_db)):
    jobs_res = await db.execute(select(Job))
    jobs = jobs_res.scalars().all()

    for job in jobs:
        await db.delete(job)
        job_dir = OUTPUT_DIR / job.id
        if job_dir.exists() and job_dir.is_dir():
            try:
                shutil.rmtree(job_dir)
            except Exception as e:
                logger.error(f"Failed to delete directory {job_dir}: {e}")

    await db.commit()
    return {"message": "All jobs deleted successfully"}


@app.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.delete(job)
    await db.commit()

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


def get_local_files(job_id: str, exclude_names: set = None) -> list:
    if exclude_names is None:
        exclude_names = set()
    files = []
    job_dir = OUTPUT_DIR / job_id
    if job_dir.exists():
        for f in job_dir.glob("*"):
            if f.is_file() and f.name not in exclude_names:
                files.append(
                    {
                        "name": f.name,
                        "size": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime),
                    }
                )
    return files


def get_local_file_response(job_id: str, filename: str) -> FileResponse:
    file_path = OUTPUT_DIR / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=file_path, filename=filename, media_type="application/octet-stream"
    )


@app.get("/jobs/{job_id}/files")
async def list_job_files(job_id: str):
    files = []
    filenames = set()

    if s3_manager.enabled:
        try:
            async with s3_manager.client() as s3:
                paginator = s3.get_paginator("list_objects_v2")
                async for page in paginator.paginate(
                    Bucket=s3_manager.bucket, Prefix=f"{job_id}/"
                ):
                    for obj in page.get("Contents", []):
                        filename = os.path.basename(obj["Key"])
                        files.append(
                            {
                                "name": filename,
                                "size": obj["Size"],
                                "modified": obj["LastModified"],
                            }
                        )
                        filenames.add(filename)
        except Exception as e:
            logger.error(f"S3 List Error for job {job_id}: {e}")

    try:
        local_files = get_local_files(job_id, exclude_names=filenames)
        files.extend(local_files)
    except Exception as e:
        logger.error(f"Local File Error for job {job_id}: {e}")

    files.sort(key=lambda x: str(x["modified"]), reverse=True)
    return files


@app.get("/jobs/{job_id}/files/{filename}")
async def download_job_file(job_id: str, filename: str):
    if s3_manager.enabled:
        try:
            async with s3_manager.client() as s3_check:
                metadata = await s3_check.head_object(
                    Bucket=s3_manager.bucket, Key=f"{job_id}/{filename}"
                )

            file_size = metadata.get("ContentLength")
            content_type = metadata.get("ContentType", "application/octet-stream")

            async def s3_stream_generator():
                async with s3_manager.client() as s3:
                    obj = await s3.get_object(
                        Bucket=s3_manager.bucket, Key=f"{job_id}/{filename}"
                    )
                    async for chunk in obj["Body"].iter_chunks(chunk_size=4096):
                        yield chunk

            return StreamingResponse(
                s3_stream_generator(),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "Content-Length": str(file_size) if file_size else None,
                },
            )

        except Exception as e:
            if "404" not in str(e):
                logger.warning(f"S3 download failed for {filename}: {e}")
            pass

    logger.info(f"Fetching {filename} from local storage")
    return get_local_file_response(job_id, filename)


@app.get("/job-templates")
async def list_job_templates():
    return [
        {"name": "Awesome CV", "filename": "awesome-cv", "type": "latex"},
        {"name": "Modern Deedy", "filename": "modern-deedy", "type": "latex"},
        {"name": "Standard HTML", "filename": "resume.html.j2", "type": "html"},
    ]

# ==========================
# LATEX ENDPOINTS
# ==========================

@app.post("/jobs/{job_id}/latex/compile")
async def compile_latex(job_id: str, request: dict):
    """
    Request LaTeX compilation via RabbitMQ.

    This is async - returns immediately and compilation happens in background.
    """
    # Validate job exists
    async with get_db() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    # Publish to LaTeX compilation queue
    await rabbitmq.channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps({
                "job_id": job_id,
                "content": request["content"],
                "filename": request.get("filename", "resume.tex"),
                "engine": request.get("engine", "xelatex"),
                "create_backup": request.get("create_backup", True)
            }).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        ),
        routing_key="latex_compile"
    )

    return {
        "message": "Compilation request submitted",
        "job_id": job_id
    }


@app.get("/jobs/{job_id}/latex/source")
async def get_latex_source(job_id: str):
    """Get LaTeX source from S3."""
    s3_key = f"{job_id}/resume.tex"
    content = s3_manager.get_bytes(s3_key)

    if not content:
        raise HTTPException(status_code=404, detail="LaTeX source not found")

    return {
        "job_id": job_id,
        "content": content.decode("utf-8"),
        "s3_key": s3_key
    }


@app.put("/jobs/{job_id}/latex/source")
async def save_latex_source(job_id: str, request: dict):
    """Save LaTeX source to S3 (without compiling)."""
    s3_key = f"{job_id}/resume.tex"
    content = request["content"]

    # Create backup first
    if request.get("create_backup", True):
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_key = f"{job_id}/backups/resume_backup_{timestamp}.tex"
        s3_manager.upload_bytes(
            content.encode("utf-8"),
            backup_key,
            content_type="text/x-tex"
        )

    # Save current version
    success = s3_manager.upload_bytes(
        content.encode("utf-8"),
        s3_key,
        content_type="text/x-tex"
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save to S3")

    return {
        "success": True,
        "job_id": job_id,
        "s3_key": s3_key
    }


@app.get("/jobs/{job_id}/latex/backups")
async def list_latex_backups(job_id: str):
    """List backup versions from S3."""
    versions = s3_manager.list_versions(job_id)
    return versions
