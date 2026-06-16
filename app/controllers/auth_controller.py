from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.exceptions import AppException, DuplicateError, ValidationError
from app.services.service_factory import get_auth_service


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
            session["user_id"] = user["user_id"]
            session["nickname"] = user["nickname"]
            session["role"] = user.get("role", "user")
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


@bp.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("main.index"))
