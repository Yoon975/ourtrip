import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


class Config:
    # Real values belong in .env only (see .env.example). Never commit .env.
    _secret_key = os.getenv("SECRET_KEY", "")
    SECRET_KEY = _secret_key or "dev-only-insecure-set-SECRET_KEY-in-env"
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "our_trip_db")
    DB_CHARSET = "utf8mb4"

    UPLOAD_ROOT = BASE_DIR / "app" / "static" / "uploads"
    UPLOAD_PROFILE_DIR = UPLOAD_ROOT / "profiles"
    UPLOAD_POST_DIR = UPLOAD_ROOT / "posts"
    MAX_IMAGE_SIZE = 5 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    PASSWORD_MIN_LENGTH = 4
    PASSWORD_RESET_TOKEN_HOURS = int(os.getenv("PASSWORD_RESET_TOKEN_HOURS", "1"))
    PASSWORD_RESET_DEV_LINK = os.getenv("PASSWORD_RESET_DEV_LINK", "true").lower() == "true"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    DATA_DIR = BASE_DIR / "database"
    RECOMMENDATION_CSV = DATA_DIR / "recommendation_training.csv"
    MODEL_DIR = BASE_DIR / "app" / "models"
    RECOMMENDATION_MODEL = MODEL_DIR / "destination_rf.joblib"

    # optional: scripts/fetch_location_post_images.py (bulk/seed only)
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
