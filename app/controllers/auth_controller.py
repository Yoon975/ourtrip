from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.config import Config
from app.exceptions import AppException, DuplicateError, ValidationError
from app.services.service_factory import get_auth_service
from app.utils.csrf import regenerate_csrf_token


def _parse_register_request():
    if request.form:
        payload = {
            "email": request.form.get("u_id") or request.form.get("email"),
            "password": request.form.get("pw") or request.form.get("password"),
            "nickname": request.form.get("nick") or request.form.get("nickname"),
            "birth_year": request.form.get("birth_year"),
            "gender": request.form.get("gender", "U"),
        }
        return payload, request.files.get("profilePhoto")

    data = request.get_json(silent=True) or {}
    payload = {
        "email": data.get("u_id") or data.get("email"),
        "password": data.get("pw") or data.get("password"),
        "nickname": data.get("nick") or data.get("nickname"),
        "birth_year": data.get("birth_year") or data.get("address"),
        "gender": data.get("gender", "U"),
    }
    return payload, None


bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            user = get_auth_service().login(email, password)
            session.clear()
            session.permanent = True
            session["user_id"] = user["user_id"]
            session["nickname"] = user["nickname"]
            session["role"] = user.get("role", "user")
            regenerate_csrf_token()
            flash(f"{user['nickname']}님, 환영합니다!", "success")
            return redirect(url_for("main.index"))
        except AppException as exc:
            flash(exc.message, "error")

    return render_template("login.html")


@bp.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@bp.route("/api/user/create", methods=["POST"])
def api_create_user():
    try:
        payload, profile_file = _parse_register_request()
        user = get_auth_service().register(payload, profile_file)
        return jsonify(
            {
                "success": True,
                "message": "회원가입이 완료되었습니다!",
                "user_id": user["user_id"],
                "redirect": url_for("auth.login"),
            }
        )
    except ValidationError as exc:
        return jsonify({"success": False, "message": exc.message, "errors": exc.errors}), 422
    except DuplicateError as exc:
        return jsonify({"success": False, "message": exc.message}), 409
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    reset_url = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        try:
            result = get_auth_service().request_password_reset(email)
            flash(
                "입력하신 이메일로 등록된 계정이 있으면 비밀번호 재설정 안내가 진행됩니다.",
                "success",
            )
            if result.get("found") and result.get("dev_link_enabled"):
                reset_url = url_for("auth.reset_password", token=result["token"])
        except AppException as exc:
            flash(exc.message, "error")

    return render_template(
        "forgot_password.html",
        reset_url=reset_url,
        dev_link_enabled=Config.PASSWORD_RESET_DEV_LINK,
    )


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        try:
            get_auth_service().reset_password(
                token,
                {
                    "new_password": request.form.get("new_password", ""),
                    "confirm_password": request.form.get("confirm_password", ""),
                },
            )
            flash("비밀번호가 재설정되었습니다. 새 비밀번호로 로그인해 주세요.", "success")
            return redirect(url_for("auth.login"))
        except AppException as exc:
            flash(exc.message, "error")

    return render_template("reset_password.html", token=token)


@bp.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("main.index"))
