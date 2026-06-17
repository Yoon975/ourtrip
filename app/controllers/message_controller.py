from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.exceptions import AppException, NotFoundError
from app.services.service_factory import get_message_service, get_profile_service
from app.utils.auth_decorators import api_login_required, login_required

bp = Blueprint("message", __name__)


@bp.route("/messages")
@login_required
def inbox():
    conversations = get_message_service().list_conversations(session["user_id"])
    return render_template("messages/inbox.html", conversations=conversations)


@bp.route("/messages/<int:user_id>")
@login_required
def conversation(user_id):
    try:
        data = get_message_service().get_conversation(session["user_id"], user_id)
    except NotFoundError as exc:
        return redirect(url_for("message.inbox"))
    return render_template(
        "messages/conversation.html",
        other_user=data["other_user"],
        messages=data["messages"],
    )


@bp.route("/api/messages/<int:user_id>", methods=["POST"])
@api_login_required
def send_message(user_id):
    data = request.get_json(silent=True) or {}
    try:
        message = get_message_service().send_message(
            session["user_id"],
            user_id,
            data.get("content", ""),
        )
        return jsonify(
            {
                "success": True,
                "message": {
                    "message_id": message["message_id"],
                    "content": message["content"],
                    "sender_id": message["sender_id"],
                    "created_at": message["created_at"].strftime("%Y-%m-%d %H:%M")
                    if message.get("created_at")
                    else "",
                },
            }
        )
    except AppException as exc:
        return jsonify({"success": False, "message": exc.message}), exc.status_code


@bp.route("/profile/<int:user_id>/posts")
def user_posts(user_id):
    page = request.args.get("page", 1, type=int)
    per_page = 12
    profile = get_profile_service().get_profile(user_id)
    posts, total = get_profile_service().list_user_posts(user_id, page, per_page)
    total_pages = max((total + per_page - 1) // per_page, 1)
    return render_template(
        "user_posts.html",
        user=profile["user"],
        posts=posts,
        page=page,
        total_pages=total_pages,
        total=total,
    )
