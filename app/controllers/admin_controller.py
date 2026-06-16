from flask import Blueprint, jsonify, render_template, request, session

from app.exceptions import AppException, DuplicateError, ValidationError
from app.services.service_factory import get_admin_service
from app.utils.auth_decorators import admin_required, api_admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _parse_user_update_payload():
    if request.form:
        return {
            "nickname": request.form.get("nick") or request.form.get("nickname"),
            "email": request.form.get("email"),
            "gender": request.form.get("gender"),
            "birth_year": request.form.get("birth_year"),
            "role": request.form.get("role"),
        }

    data = request.get_json(silent=True) or {}
    return {
        "nickname": data.get("nick") or data.get("nickname"),
        "email": data.get("email"),
        "gender": data.get("gender"),
        "birth_year": data.get("birth_year"),
        "role": data.get("role"),
    }


@bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/index.html")


@bp.route("/api/overview")
@api_admin_required
def api_overview():
    overview = get_admin_service().get_overview()
    return jsonify({"success": True, "overview": overview})


@bp.route("/api/users")
@api_admin_required
def api_users():
    page = request.args.get("page", 1, type=int)
    role = request.args.get("role") or None
    search = request.args.get("q", "").strip() or None
    data = get_admin_service().serialize_users_page(get_admin_service().list_users(page, role, search))
    return jsonify({"success": True, **data})


@bp.route("/api/posts")
@api_admin_required
def api_posts():
    page = request.args.get("page", 1, type=int)
    country = request.args.get("country") or None
    search = request.args.get("q", "").strip() or None
    data = get_admin_service().serialize_posts_page(get_admin_service().list_posts(page, country, search))
    countries = get_admin_service().list_countries()
    return jsonify({"success": True, "countries": countries, **data})


@bp.route("/api/comments")
@api_admin_required
def api_comments():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip() or None
    data = get_admin_service().serialize_comments_page(get_admin_service().list_comments(page, search))
    return jsonify({"success": True, **data})


@bp.route("/api/scraps")
@api_admin_required
def api_scraps():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip() or None
    data = get_admin_service().serialize_scraps_page(get_admin_service().list_scraps(page, search))
    return jsonify({"success": True, **data})


@bp.route("/api/contacts")
@api_admin_required
def api_contacts():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip() or None
    data = get_admin_service().serialize_contacts_page(get_admin_service().list_contacts(page, search))
    return jsonify({"success": True, **data})


@bp.route("/api/model/train", methods=["POST"])
@api_admin_required
def api_train_model():
    try:
        result = get_admin_service().train_recommendation_model()
        return jsonify(
            {
                "success": True,
                "message": "추천 모델이 생성되었습니다.",
                "model": result,
            }
        )
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/users/<int:user_id>", methods=["POST"])
@api_admin_required
def api_update_user(user_id):
    try:
        payload = _parse_user_update_payload()
        result = get_admin_service().update_user(user_id, payload)

        if session.get("user_id") == user_id:
            session["nickname"] = result["nickname"]
            session["role"] = result["role"]

        return jsonify({"success": True, "message": "회원 정보가 수정되었습니다.", "user": result})
    except ValidationError as exc:
        return jsonify({"success": False, "message": exc.message, "errors": exc.errors}), 422
    except DuplicateError as exc:
        return jsonify({"success": False, "message": exc.message}), 409
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@api_admin_required
def api_delete_user(user_id):
    try:
        if session.get("user_id") == user_id:
            return jsonify({"success": False, "message": "본인 계정은 삭제할 수 없습니다."}), 400
        get_admin_service().delete_user(user_id)
        return jsonify({"success": True, "message": "회원이 삭제되었습니다."})
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/posts/<int:post_id>", methods=["DELETE"])
@api_admin_required
def api_delete_post(post_id):
    try:
        get_admin_service().delete_post(post_id)
        return jsonify({"success": True, "message": "게시글이 삭제되었습니다."})
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/comments/<int:comment_id>", methods=["DELETE"])
@api_admin_required
def api_delete_comment(comment_id):
    try:
        get_admin_service().delete_comment(comment_id)
        return jsonify({"success": True, "message": "댓글이 삭제되었습니다."})
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/scraps/<int:scrap_id>", methods=["DELETE"])
@api_admin_required
def api_delete_scrap(scrap_id):
    try:
        get_admin_service().delete_scrap(scrap_id)
        return jsonify({"success": True, "message": "스크랩이 삭제되었습니다."})
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
@api_admin_required
def api_delete_contact(contact_id):
    try:
        get_admin_service().delete_contact(contact_id)
        return jsonify({"success": True, "message": "문의가 삭제되었습니다."})
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code
