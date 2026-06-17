import secrets

from flask import request, session

from app.exceptions import ForbiddenError

CSRF_SESSION_KEY = "_csrf_token"


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(32)
        session[CSRF_SESSION_KEY] = token
    return token


def regenerate_csrf_token():
    token = secrets.token_hex(32)
    session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf():
    session_token = session.get(CSRF_SESSION_KEY)
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not session_token or not submitted:
        raise ForbiddenError("잘못된 요청입니다. 페이지를 새로고침 후 다시 시도해 주세요.")
    if not secrets.compare_digest(str(session_token), str(submitted)):
        raise ForbiddenError("잘못된 요청입니다. 페이지를 새로고침 후 다시 시도해 주세요.")
