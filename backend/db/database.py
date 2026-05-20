import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in your .env file")

# Detect if using Supabase connection pooler
# Pooler connections don't support pool_size/max_overflow
IS_POOLED = "pooler.supabase.com" in DATABASE_URL

if IS_POOLED:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency — yields a database session for each request
    and ensures it is closed when the request finishes, even if an
    error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()