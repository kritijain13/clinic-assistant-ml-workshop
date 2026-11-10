import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

from src.logger import get_logger


# .env file ka path
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


# Logger
logger = get_logger(__name__)


# MySQL settings
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")


# Validate configuration without including values in the error message.
_required_settings = {
    "MYSQL_HOST": MYSQL_HOST,
    "MYSQL_PORT": MYSQL_PORT,
    "MYSQL_USER": MYSQL_USER,
    "MYSQL_PASSWORD": MYSQL_PASSWORD,
    "MYSQL_DATABASE": MYSQL_DATABASE,
}
_missing_settings = [name for name, value in _required_settings.items() if not value]
if _missing_settings:
    raise RuntimeError(
        "Database configuration is incomplete. Set: "
        + ", ".join(_missing_settings)
    )

try:
    MYSQL_PORT = int(MYSQL_PORT)
except ValueError as exc:
    raise RuntimeError("Database configuration error: MYSQL_PORT must be an integer") from exc


# SQLAlchemy URL.create keeps credentials safely escaped and applies TLS verification.
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    database=MYSQL_DATABASE,
    query={
        "ssl_verify_cert": "true",
        "ssl_verify_identity": "true",
    },
)


# Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)


# Create session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base class for database models
Base = declarative_base()


# Database dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
