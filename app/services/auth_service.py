from app.config import Config
from app.exceptions import DuplicateError, ForbiddenError, NotFoundError, UnauthorizedError, ValidationError
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.user_repository import UserRepository
from app.services.image_service import ImageService
from app.utils.security import hash_password, verify_password
from app.validators.auth_validator import (
    validate_email_change_payload,
    validate_login_payload,
    validate_password_change_payload,
    validate_password_reset_payload,
    validate_password_reset_request_payload,
    validate_signup_payload,
    validate_withdraw_payload,
)


class AuthService:
    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.reset_repo = PasswordResetRepository(db)
        self.image_service = ImageService()

    def register(self, payload, profile_file=None):
        email = (payload.get("email") or payload.get("u_id") or "").strip()
        password = payload.get("password") or payload.get("pw") or ""
        nickname = (payload.get("nickname") or payload.get("nick") or "").strip()
        birth_year_raw = payload.get("birth_year")
        birth_year = int(birth_year_raw) if birth_year_raw not in (None, "") else None
        gender = payload.get("gender", "U")

        validate_signup_payload(
            {
                "email": email,
                "password": password,
                "nickname": nickname,
                "birth_year": birth_year,
                "gender": gender,
            }
        )

        profile_image_url = None
        if profile_file:
            profile_image_url = self.image_service.save_profile_image(profile_file)

        password_hash = hash_password(password)
        user_id = self.user_repo.create(
            email=email,
            password_hash=password_hash,
            nickname=nickname,
            gender=gender,
            birth_year=birth_year,
            profile_image_url=profile_image_url,
        )
        return {"user_id": user_id, "email": email, "nickname": nickname}

    def login(self, email, password):
        validate_login_payload({"email": email, "password": password})
        user = self.user_repo.find_by_email(email.strip())
        if not user or not verify_password(user["password"], password):
            raise UnauthorizedError("이메일 또는 비밀번호가 올바르지 않습니다.")
        return {
            "user_id": user["user_id"],
            "nickname": user["nickname"],
            "role": user.get("role", "user"),
            "email": user["email"],
        }

    def change_password(self, user_id, payload):
        validate_password_change_payload(payload)
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        if not verify_password(user["password"], payload["current_password"]):
            raise UnauthorizedError("현재 비밀번호가 올바르지 않습니다.")
        self.user_repo.update_password(user_id, hash_password(payload["new_password"]))
        self.reset_repo.delete_by_user(user_id)
        return {"message": "비밀번호가 변경되었습니다."}

    def change_email(self, user_id, payload):
        validate_email_change_payload(payload)
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        if not verify_password(user["password"], payload["password"]):
            raise UnauthorizedError("비밀번호가 올바르지 않습니다.")

        new_email = payload["new_email"].strip()
        if new_email.lower() == (user["email"] or "").lower():
            raise ValidationError("현재 이메일과 다른 주소를 입력해 주세요.", errors={"new_email": "동일한 이메일"})

        self.user_repo.update_email(user_id, new_email)
        return {"message": "이메일이 변경되었습니다.", "email": new_email}

    def withdraw_account(self, user_id, payload):
        validate_withdraw_payload(payload)
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        if user.get("role") == "admin":
            raise ForbiddenError("관리자 계정은 탈퇴할 수 없습니다. 다른 관리자에게 문의하세요.")
        if not verify_password(user["password"], payload["password"]):
            raise UnauthorizedError("비밀번호가 올바르지 않습니다.")

        if user.get("profile_image_url"):
            self.image_service.delete_relative(user["profile_image_url"])
        self.user_repo.delete_by_id(user_id)
        return {"message": "회원 탈퇴가 완료되었습니다."}

    def request_password_reset(self, email):
        validate_password_reset_request_payload({"email": email})
        user = self.user_repo.find_by_email(email.strip())
        if not user:
            return {"found": False, "reset_url": None}

        raw_token = self.reset_repo.create_token(user["user_id"])
        return {
            "found": True,
            "token": raw_token,
            "dev_link_enabled": Config.PASSWORD_RESET_DEV_LINK,
        }

    def reset_password(self, raw_token, payload):
        validate_password_reset_payload(payload)
        token_row = self.reset_repo.find_valid_token(raw_token)
        if not token_row:
            raise ValidationError("만료되었거나 유효하지 않은 재설정 링크입니다.")

        user_id = token_row["user_id"]
        self.user_repo.update_password(user_id, hash_password(payload["new_password"]))
        self.reset_repo.mark_used(token_row["token_id"])
        self.reset_repo.delete_by_user(user_id)
        return {"message": "비밀번호가 재설정되었습니다. 새 비밀번호로 로그인해 주세요."}

    def get_account_summary(self, user_id):
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "nickname": user["nickname"],
            "role": user.get("role", "user"),
        }
