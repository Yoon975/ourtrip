from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.exceptions import AppException, DuplicateError, ForbiddenError, UnauthorizedError, ValidationError
from app.services.service_factory import get_auth_service, get_profile_service
from app.utils.auth_decorators import api_login_required, login_required
from app.utils.csrf import regenerate_csrf_token

bp = Blueprint("profile", __name__)


def _parse_profile_update_request():
    if request.form:
        payload = {
            "nickname": request.form.get("nick") or request.form.get("nickname"),
            "birth_year": request.form.get("birth_year"),
            "gender": request.form.get("gender"),
            "bio": request.form.get("bio"),
            "profile_role": request.form.get("profile_role"),
        }
        return payload, request.files.get("profilePhoto")

    data = request.get_json(silent=True) or {}
    payload = {
        "nickname": data.get("nick") or data.get("nickname"),
        "birth_year": data.get("birth_year"),
        "gender": data.get("gender"),
        "bio": data.get("bio"),
        "profile_role": data.get("profile_role"),
    }
    return payload, None


@bp.route("/profile")
def my_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    return redirect(url_for("profile.view_profile", user_id=user_id))


@bp.route("/profile/edit")
@login_required
def edit_profile():
    user_id = session.get("user_id")
    profile = get_profile_service().get_profile(user_id)
    return render_template(
        "profile_edit.html",
        user=profile["user"],
        gender_label=profile["gender_label"],
    )


@bp.route("/api/profile/update", methods=["POST"])
@api_login_required
def api_update_profile():
    try:
        user_id = session.get("user_id")
        payload, profile_file = _parse_profile_update_request()
        result = get_profile_service().update_profile(user_id, payload, profile_file)
        session["nickname"] = result["nickname"]
        return jsonify(
            {
                "success": True,
                "message": "프로필이 수정되었습니다.",
                "redirect": url_for("profile.view_profile", user_id=user_id),
            }
        )
    except ValidationError as exc:
        return jsonify({"success": False, "message": exc.message, "errors": exc.errors}), 422
    except DuplicateError as exc:
        return jsonify({"success": False, "message": exc.message}), 409
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/profile/account")
@login_required
def account_settings():
    summary = get_auth_service().get_account_summary(session["user_id"])
    return render_template("account_settings.html", account=summary)


@bp.route("/api/account/password", methods=["POST"])
@api_login_required
def api_change_password():
    try:
        data = request.get_json(silent=True) or {}
        get_auth_service().change_password(
            session["user_id"],
            {
                "current_password": data.get("current_password", ""),
                "new_password": data.get("new_password", ""),
                "confirm_password": data.get("confirm_password", ""),
            },
        )
        regenerate_csrf_token()
        return jsonify({"success": True, "message": "비밀번호가 변경되었습니다."})
    except ValidationError as exc:
        return jsonify({"success": False, "message": exc.message, "errors": exc.errors}), 422
    except UnauthorizedError as exc:
        return jsonify({"success": False, "message": exc.message}), 401
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/account/email", methods=["POST"])
@api_login_required
def api_change_email():
    try:
        data = request.get_json(silent=True) or {}
        result = get_auth_service().change_email(
            session["user_id"],
            {
                "new_email": data.get("new_email", ""),
                "password": data.get("password", ""),
            },
        )
        return jsonify({"success": True, "message": result["message"], "email": result["email"]})
    except ValidationError as exc:
        return jsonify({"success": False, "message": exc.message, "errors": exc.errors}), 422
    except DuplicateError as exc:
        return jsonify({"success": False, "message": exc.message}), 409
    except UnauthorizedError as exc:
        return jsonify({"success": False, "message": exc.message}), 401
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/account/withdraw", methods=["POST"])
@api_login_required
def api_withdraw_account():
    try:
        data = request.get_json(silent=True) or {}
        get_auth_service().withdraw_account(
            session["user_id"],
            {
                "password": data.get("password", ""),
                "confirm_text": data.get("confirm_text", ""),
            },
        )
        session.clear()
        return jsonify(
            {
                "success": True,
                "message": "회원 탈퇴가 완료되었습니다.",
                "redirect": url_for("main.index"),
            }
        )
    except ValidationError as exc:
        return jsonify({"success": False, "message": exc.message, "errors": exc.errors}), 422
    except ForbiddenError as exc:
        return jsonify({"success": False, "message": exc.message}), 403
    except UnauthorizedError as exc:
        return jsonify({"success": False, "message": exc.message}), 401
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/profile/<int:user_id>")
def view_profile(user_id):
    profile = get_profile_service().get_profile(user_id)
    return render_template(
        "profile.html",
        user=profile["user"],
        stats=profile["stats"],
        countries=profile["countries"],
        recent_posts=profile["recent_posts"],
        scraped_posts=profile["scraped_posts"],
        gender_label=profile["gender_label"],
    )
