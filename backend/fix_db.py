import asyncio
import logging

from database import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_missing_columns():
    async with engine.connect() as conn:
        # 1. Add root_job_id column
        try:
            logger.info("Attempting to add root_job_id column...")
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN root_job_id VARCHAR"))
            await conn.execute(
                text("CREATE INDEX ix_jobs_root_job_id ON jobs (root_job_id)")
            )
            # Backfill existing jobs to be their own root
            await conn.execute(
                text("UPDATE jobs SET root_job_id = id WHERE root_job_id IS NULL")
            )
            await conn.commit()
            logger.info("Successfully added root_job_id.")
        except Exception as e:
            logger.warning(f"Could not add root_job_id (might already exist): {e}")
            await conn.rollback()

        # 2. Add foreign key constraint to user_id if missing
        try:
            logger.info("Attempting to add Foreign Key constraint to jobs.user_id...")
            await conn.execute(
                text(
                    "ALTER TABLE jobs ADD CONSTRAINT fk_jobs_users FOREIGN KEY (user_id) REFERENCES users(id)"
                )
            )
            await conn.commit()
            logger.info("Successfully added FK constraint.")
        except Exception as e:
            logger.warning(f"Could not add FK constraint (might already exist): {e}")
            await conn.rollback()

        # 3. Add location column to career_education
        try:
            logger.info("Attempting to add location column to career_education...")
            await conn.execute(
                text("ALTER TABLE career_education ADD COLUMN location VARCHAR")
            )
            await conn.commit()
            logger.info("Successfully added location column to career_education.")
        except Exception as e:
            logger.warning(
                f"Could not add location to career_education (might already exist): {e}"
            )
            await conn.rollback()

        # 4. Add critique_json column to jobs
        try:
            logger.info("Attempting to add critique_json column to jobs...")
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN critique_json JSON"))
            await conn.commit()
            logger.info("Successfully added critique_json column to jobs.")
        except Exception as e:
            logger.warning(
                f"Could not add critique_json to jobs (might already exist): {e}"
            )
            await conn.rollback()


if __name__ == "__main__":
    asyncio.run(add_missing_columns())
