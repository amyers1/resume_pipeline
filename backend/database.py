import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Note the +asyncpg driver
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/resume_pipeline",
)

# Async Engine
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Async Session Factory
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


# Async Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Legacy Synchronous Version
# import os

# from sqlalchemy import create_engine
# from sqlalchemy.orm import declarative_base, sessionmaker

# DATABASE_URL = os.getenv(
#     "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/resume_pipeline"
# )

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()

# def get_db():
#     """Dependency for FastAPI to get DB session."""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
