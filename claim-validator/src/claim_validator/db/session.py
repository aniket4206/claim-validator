"""SQLAlchemy engine and session factory.

Reads DB_* variables from the environment / .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env from project root
_this_dir = Path(__file__).resolve().parent
for _candidate in [_this_dir.parent.parent.parent.parent, _this_dir.parent.parent.parent]:
    _env = _candidate / ".env"
    if _env.is_file():
        load_dotenv(_env)
        break


def _build_database_url() -> str:
    driver = os.getenv("DB_CONNECTION", "mysql")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    database = os.getenv("DB_DATABASE", "EligibilityAgent")
    username = os.getenv("DB_USERNAME", "root")
    password = os.getenv("DB_PASSWORD", "")

    # URL-encode password to handle special characters like @, #, etc.
    encoded_password = quote_plus(password)

    if driver == "mysql":
        return f"mysql+pymysql://{username}:{encoded_password}@{host}:{port}/{database}?charset=utf8mb4"
    elif driver == "postgresql":
        return f"postgresql+psycopg2://{username}:{encoded_password}@{host}:{port}/{database}"
    elif driver == "sqlite":
        return f"sqlite:///{database}"
    else:
        return f"{driver}+pymysql://{username}:{encoded_password}@{host}:{port}/{database}"


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Yield a database session (for FastAPI Depends)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
