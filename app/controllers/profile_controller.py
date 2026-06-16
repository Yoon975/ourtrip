from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.exceptions import AppException, DuplicateError, ValidationError
from app.services.service_factory import get_profile_service
from app.utils.auth_decorators import api_login_required, login_required

bp = Blueprint("profile", __name__)


def _parse_profile_update_request():
    if request.form:
        payload = {
            "nickname": request.form.get("nick") or request.form.get("nickname"),
            "birth_year": request.form.get("birth_year"),
            "gender": request.form.get("gender"),
        }
        return payload, request.files.get("profilePhoto")

    data = request.get_json(silent=True) or {}
    payload = {
        "nickname": data.get("nick") or data.get("nickname"),
        "birth_year": data.get("birth_year"),
        "gender": data.get("gender"),
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
