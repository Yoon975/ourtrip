import hashlib
import secrets
from datetime import datetime, timedelta

from app.config import Config


class PasswordResetRepository:
    def __init__(self, db):
        self.db = db

    def create_token(self, user_id):
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now() + timedelta(hours=Config.PASSWORD_RESET_TOKEN_HOURS)
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO PasswordResetTokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, token_hash, expires_at),
            )
        self.db.commit()
        return raw_token

    def find_valid_token(self, raw_token):
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT token_id, user_id, expires_at, used_at
                FROM PasswordResetTokens
                WHERE token_hash = %s
                """,
                (token_hash,),
            )
            row = cursor.fetchone()
        if not row or row.get("used_at"):
            return None
        if row["expires_at"] < datetime.now():
            return None
        return row

    def mark_used(self, token_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE PasswordResetTokens
                SET used_at = CURRENT_TIMESTAMP
                WHERE token_id = %s
                """,
                (token_id,),
            )
        self.db.commit()

    def delete_by_user(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute("DELETE FROM PasswordResetTokens WHERE user_id = %s", (user_id,))
        self.db.commit()
