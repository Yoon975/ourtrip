import re
from datetime import datetime

from app.config import Config
from app.exceptions import ValidationError

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_required_fields(data, fields):
    errors = {}
    for field in fields:
        value = data.get(field)
        if value is None or str(value).strip() == "":
            errors[field] = "필수 입력 항목입니다."
    return errors


def validate_email(email):
    email = (email or "").strip()
    if not email:
        return "이메일을 입력해 주세요."
    if len(email) > 100:
        return "이메일은 100자 이하여야 합니다."
    if not EMAIL_PATTERN.match(email):
        return "올바른 이메일 형식이 아닙니다."
    return None


def validate_password(password):
    password = password or ""
    if not password:
        return "비밀번호를 입력해 주세요."
    if len(password) < Config.PASSWORD_MIN_LENGTH:
        return f"비밀번호는 {Config.PASSWORD_MIN_LENGTH}자 이상이어야 합니다."
    if len(password) > 128:
        return "비밀번호는 128자 이하여야 합니다."
    return None


def validate_nickname(nickname):
    nickname = (nickname or "").strip()
    if not nickname:
        return "닉네임을 입력해 주세요."
    if len(nickname) > 50:
        return "닉네임은 50자 이하여야 합니다."
    return None


def validate_birth_year(value):
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text.isdigit():
        return "출생년도는 숫자로 입력해 주세요."
    year = int(text)
    if year < 1900 or year > datetime.now().year:
        return "출생년도가 올바르지 않습니다."
    return None


def validate_gender(value):
    if value not in ("M", "F"):
        return "성별을 선택해 주세요."
    return None


def validate_signup_payload(data):
    errors = {}
    email_error = validate_email(data.get("email"))
    password_error = validate_password(data.get("password"))
    nickname_error = validate_nickname(data.get("nickname"))
    birth_error = validate_birth_year(data.get("birth_year"))
    gender_error = validate_gender(data.get("gender"))

    if email_error:
        errors["email"] = email_error
    if password_error:
        errors["password"] = password_error
    if nickname_error:
        errors["nickname"] = nickname_error
    if birth_error:
        errors["birth_year"] = birth_error
    if gender_error:
        errors["gender"] = gender_error

    if errors:
        raise ValidationError("입력값을 확인해 주세요.", errors=errors)


def validate_profile_update_payload(data):
    errors = {}
    nickname_error = validate_nickname(data.get("nickname"))
    birth_error = validate_birth_year(data.get("birth_year"))
    gender_error = validate_gender(data.get("gender"))

    if nickname_error:
        errors["nickname"] = nickname_error
    if birth_error:
        errors["birth_year"] = birth_error
    if gender_error:
        errors["gender"] = gender_error

    if errors:
        raise ValidationError("입력값을 확인해 주세요.", errors=errors)


def validate_role(value):
    if value not in ("user", "admin"):
        return "올바른 권한을 선택해 주세요."
    return None


def validate_admin_user_update(data):
    errors = {}
    nickname_error = validate_nickname(data.get("nickname"))
    birth_error = validate_birth_year(data.get("birth_year"))
    gender_error = validate_gender(data.get("gender"))
    role_error = validate_role(data.get("role"))

    if nickname_error:
        errors["nickname"] = nickname_error
    if birth_error:
        errors["birth_year"] = birth_error
    if gender_error:
        errors["gender"] = gender_error
    if role_error:
        errors["role"] = role_error

    if errors:
        raise ValidationError("입력값을 확인해 주세요.", errors=errors)


def validate_login_payload(data):
    errors = {}
    email_error = validate_email(data.get("email"))
    password_error = validate_password(data.get("password"))
    if email_error:
        errors["email"] = email_error
    if password_error:
        errors["password"] = password_error
    if errors:
        raise ValidationError("로그인 정보를 확인해 주세요.", errors=errors)


def validate_comment_content(content):
    content = (content or "").strip()
    if not content:
        raise ValidationError("댓글 내용을 입력해 주세요.", errors={"content": "필수 입력"})
    if len(content) > 1000:
        raise ValidationError("댓글은 1000자 이하여야 합니다.", errors={"content": "길이 초과"})
    return content


def validate_scrap_payload(data):
    post_id = data.get("post_id")
    if post_id is None:
        raise ValidationError("post_id가 필요합니다.", errors={"post_id": "필수"})
    try:
        return int(post_id)
    except (TypeError, ValueError):
        raise ValidationError("post_id 형식이 올바르지 않습니다.", errors={"post_id": "형식 오류"})
