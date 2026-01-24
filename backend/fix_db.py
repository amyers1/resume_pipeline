import logging

from database import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_missing_columns():
    with engine.connect() as conn:
        # 1. Add root_job_id column
        try:
            logger.info("Attempting to add root_job_id column...")
            conn.execute(text("ALTER TABLE jobs ADD COLUMN root_job_id VARCHAR"))
            conn.execute(text("CREATE INDEX ix_jobs_root_job_id ON jobs (root_job_id)"))
            # Backfill existing jobs to be their own root
            conn.execute(
                text("UPDATE jobs SET root_job_id = id WHERE root_job_id IS NULL")
            )
            conn.commit()
            logger.info("Successfully added root_job_id.")
        except Exception as e:
            logger.warning(f"Could not add root_job_id (might already exist): {e}")
            conn.rollback()

        # 2. Add foreign key constraint to user_id if missing
        try:
            logger.info("Attempting to add Foreign Key constraint to jobs.user_id...")
            conn.execute(
                text(
                    "ALTER TABLE jobs ADD CONSTRAINT fk_jobs_users FOREIGN KEY (user_id) REFERENCES users(id)"
                )
            )
            conn.commit()
            logger.info("Successfully added FK constraint.")
        except Exception as e:
            logger.warning(f"Could not add FK constraint (might already exist): {e}")
            conn.rollback()


if __name__ == "__main__":
    add_missing_columns()
