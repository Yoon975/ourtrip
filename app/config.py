import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "our-trip-dev-secret")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
    DB_NAME = os.getenv("DB_NAME", "our_trip_db")
    DB_CHARSET = "utf8mb4"

    UPLOAD_ROOT = BASE_DIR / "app" / "static" / "uploads"
    UPLOAD_PROFILE_DIR = UPLOAD_ROOT / "profiles"
    UPLOAD_POST_DIR = UPLOAD_ROOT / "posts"
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    PASSWORD_MIN_LENGTH = 4

    DATA_DIR = BASE_DIR / "database"
    RECOMMENDATION_CSV = DATA_DIR / "recommendation_training.csv"
    MODEL_DIR = BASE_DIR / "app" / "models"
    RECOMMENDATION_MODEL = MODEL_DIR / "destination_rf.joblib"
