from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.exceptions import AppException, ForbiddenError, NotFoundError, ValidationError
from app.services.service_factory import (
    get_comment_service,
    get_contact_service,
    get_notification_service,
    get_post_service,
    get_recommendation_service,
    get_scrap_service,
)
from app.utils.auth_decorators import api_login_required, login_required
from app.validators.auth_validator import validate_scrap_payload

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    user_id = session.get("user_id")
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip() or None
    country = request.args.get("country", "").strip() or None
    city = request.args.get("city", "").strip() or None
    per_page = 12
    posts, total_posts = get_post_service().list_posts(
        page=page,
        per_page=per_page,
        search=search,
        country=country,
        city=city,
    )
    total_pages = max((total_posts + per_page - 1) // per_page, 1)
    recommendations = get_recommendation_service().get_recommendations(user_id=user_id, limit=3)
    return render_template(
        "index.html",
        posts=posts,
        page=page,
        total_pages=total_pages,
        total_posts=total_posts,
        search=search or "",
        country=country or "",
        city=city or "",
        countries=get_post_service().list_countries(),
        recommended=recommendations["posts"],
        recommended_destinations=recommendations["destinations"],
        model_ready=recommendations.get("model_ready", False),
    )


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        try:
            get_contact_service().submit_contact(
                name=request.form.get("name"),
                email=request.form.get("email"),
                message=request.form.get("message"),
                user_id=session.get("user_id"),
            )
            flash(f"{request.form.get('name', '').strip()}님, 문의가 접수되었습니다.", "success")
            return redirect(url_for("main.contact"))
        except ValidationError as exc:
            flash(exc.message, "error")
            return render_template("contact.html", form=request.form, errors=exc.errors)
    return render_template("contact.html", form={}, errors={})


@bp.route("/write", methods=["GET", "POST"])
@login_required
def write_post():
    if request.method == "POST":
        try:
            post_id = get_post_service().create_post(
                user_id=session["user_id"],
                payload=request.form,
                image_files=request.files.getlist("images"),
                image_file=request.files.get("image"),
            )
            flash("여행 글이 등록되었습니다!", "success")
            return redirect(url_for("main.post_detail", post_id=post_id))
        except ValidationError as exc:
            flash(exc.message, "error")
            return render_template("write.html", form=request.form, errors=exc.errors)

    return render_template("write.html", form={}, errors={}, edit_mode=False)


@bp.route("/posts/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    try:
        if request.method == "POST":
            get_post_service().update_post(
                user_id=session["user_id"],
                post_id=post_id,
                payload=request.form,
                image_files=request.files.getlist("images"),
                replace_images=request.form.get("replace_images") == "1",
            )
            flash("게시글이 수정되었습니다.", "success")
            return redirect(url_for("main.post_detail", post_id=post_id))

        post = get_post_service().get_post_for_edit(session["user_id"], post_id)
        start = post.get("travel_start_date")
        end = post.get("travel_end_date")
        form = {
            "title": post["title"],
            "content": post["content"],
            "location_country": post["location_country"],
            "location_city": post.get("location_city") or "",
            "travel_start_date": start.isoformat() if start else "",
            "travel_end_date": end.isoformat() if end else "",
        }
        return render_template(
            "write.html",
            form=form,
            errors={},
            edit_mode=True,
            post=post,
        )
    except (NotFoundError, ForbiddenError) as exc:
        flash(exc.message, "error")
        return redirect(url_for("main.index"))


@bp.route("/posts/<int:post_id>", methods=["DELETE"])
@api_login_required
def delete_post(post_id):
    try:
        get_post_service().delete_post(session["user_id"], post_id)
        return jsonify({"success": True, "message": "게시글이 삭제되었습니다."})
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/posts/<int:post_id>")
def post_detail(post_id):
    try:
        detail = get_post_service().get_post_detail(post_id, session.get("user_id"))
    except NotFoundError as exc:
        flash(exc.message, "error")
        return redirect(url_for("main.index"))

    return render_template(
        "post_detail.html",
        post=detail["post"],
        comments=detail["comments"],
        is_scraped=detail["is_scraped"],
        scrap_count=detail["scrap_count"],
        can_edit=detail.get("can_edit", False),
    )


@bp.route("/scraps")
@login_required
def my_scraps():
    page = request.args.get("page", 1, type=int)
    per_page = 12
    items, total = get_scrap_service().list_user_scraps(session["user_id"], page, per_page)
    total_pages = max((total + per_page - 1) // per_page, 1)
    return render_template(
        "scraps.html",
        scraps=items,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@bp.route("/api/scraps/toggle", methods=["POST"])
@api_login_required
def toggle_scrap():
    data = request.get_json(silent=True) or {}
    post_id = validate_scrap_payload(data)
    result = get_scrap_service().toggle_scrap(session["user_id"], post_id)
    return jsonify({"success": True, **result})


@bp.route("/api/comments", methods=["POST"])
@api_login_required
def create_comment():
    data = request.get_json(silent=True) or {}
    post_id = int(data.get("post_id"))
    parent_id = data.get("parent_id")
    parent_id = int(parent_id) if parent_id not in (None, "") else None

    try:
        comment = get_comment_service().add_comment(
            post_id=post_id,
            user_id=session["user_id"],
            content=data.get("content", ""),
            parent_id=parent_id,
        )
        return jsonify(
            {
                "success": True,
                "comment": {
                    "comment_id": comment["comment_id"],
                    "nickname": comment["nickname"],
                    "content": comment["content"],
                    "parent_id": comment.get("parent_id"),
                    "created_at": comment["created_at"].strftime("%Y.%m.%d")
                    if comment.get("created_at")
                    else "",
                },
            }
        )
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/comments/<int:comment_id>", methods=["PUT", "PATCH"])
@api_login_required
def update_comment(comment_id):
    data = request.get_json(silent=True) or {}
    try:
        comment = get_comment_service().update_comment(
            session["user_id"],
            comment_id,
            data.get("content", ""),
        )
        return jsonify({"success": True, "comment": {"comment_id": comment["comment_id"], "content": comment["content"]}})
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/comments/<int:comment_id>", methods=["DELETE"])
@api_login_required
def delete_comment(comment_id):
    try:
        get_comment_service().delete_comment(session["user_id"], comment_id)
        return jsonify({"success": True, "message": "댓글이 삭제되었습니다."})
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/api/notifications")
@api_login_required
def list_notifications():
    items = get_notification_service().list_notifications(session["user_id"])
    payload = []
    for item in items:
        payload.append(
            {
                "notification_id": item["notification_id"],
                "type": item["type"],
                "content": item["content"],
                "link_url": item.get("link_url"),
                "is_read": bool(item.get("is_read")),
                "created_at": item["created_at"].strftime("%Y-%m-%d %H:%M")
                if item.get("created_at")
                else "",
                "actor_nickname": item.get("actor_nickname"),
            }
        )
    return jsonify({"success": True, "items": payload})


@bp.route("/api/notifications/read-all", methods=["POST"])
@api_login_required
def read_all_notifications():
    get_notification_service().mark_all_read(session["user_id"])
    return jsonify({"success": True})


@bp.route("/api/recommendations")
def recommendations():
    user_id = session.get("user_id")
    items = get_recommendation_service().get_recommendations(user_id=user_id, limit=5)
    return jsonify(
        {
            "success": True,
            "destinations": items["destinations"],
            "user_features": items.get("user_features"),
            "model_ready": items.get("model_ready", False),
            "items": [
                {
                    "post_id": post["post_id"],
                    "title": post["title"],
                    "location_country": post.get("location_country"),
                    "location_city": post.get("location_city"),
                    "image_url": post.get("image_url"),
                    "recommendation_score": post.get("recommendation_score"),
                }
                for post in items["posts"]
            ],
        }
    )
