from app.exceptions import DuplicateError, NotFoundError, UnauthorizedError
from app.repositories.user_repository import UserRepository
from app.services.image_service import ImageService
from app.utils.security import hash_password, verify_password
from app.validators.auth_validator import validate_login_payload, validate_signup_payload


class AuthService:
    def __init__(self, db):
        self.user_repo = UserRepository(db)
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
        }
