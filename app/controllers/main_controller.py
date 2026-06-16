from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.exceptions import NotFoundError, ValidationError
from app.services.service_factory import (
    get_comment_service,
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
    per_page = 12
    posts, total_posts = get_post_service().list_posts(page=page, per_page=per_page)
    total_pages = max((total_posts + per_page - 1) // per_page, 1)
    recommendations = get_recommendation_service().get_recommendations(user_id=user_id, limit=3)
    return render_template(
        "index.html",
        posts=posts,
        page=page,
        total_pages=total_pages,
        total_posts=total_posts,
        recommended=recommendations["posts"],
        recommended_destinations=recommendations["destinations"],
    )


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        flash(f"{name}님, 문의가 접수되었습니다.", "success")
        return redirect(url_for("main.contact"))
    return render_template("contact.html")


@bp.route("/write", methods=["GET", "POST"])
@login_required
def write_post():
    if request.method == "POST":
        try:
            post_id = get_post_service().create_post(
                user_id=session["user_id"],
                payload=request.form,
                image_file=request.files.get("image"),
            )
            flash("여행 글이 등록되었습니다!", "success")
            return redirect(url_for("main.post_detail", post_id=post_id))
        except ValidationError as exc:
            flash(exc.message, "error")
            return render_template("write.html", form=request.form, errors=exc.errors)

    return render_template("write.html", form={}, errors={})


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


@bp.route("/api/recommendations")
def recommendations():
    user_id = session.get("user_id")
    items = get_recommendation_service().get_recommendations(user_id=user_id, limit=5)
    return jsonify(
        {
            "success": True,
            "destinations": items["destinations"],
            "user_features": items.get("user_features"),
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
