from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.db import get_db

bp = Blueprint("main", __name__)


def _fetch_posts():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.*, u.nickname,
                   (SELECT image_url FROM Post_Images pi
                    WHERE pi.post_id = p.post_id
                    ORDER BY pi.image_order LIMIT 1) AS image_url
            FROM Posts p
            JOIN Users u ON p.user_id = u.user_id
            ORDER BY p.created_at DESC
            """
        )
        return cursor.fetchall()


def _fetch_post(post_id):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT p.*, u.nickname,
                   (SELECT image_url FROM Post_Images pi
                    WHERE pi.post_id = p.post_id
                    ORDER BY pi.image_order LIMIT 1) AS image_url
            FROM Posts p
            JOIN Users u ON p.user_id = u.user_id
            WHERE p.post_id = %s
            """,
            (post_id,),
        )
        post = cursor.fetchone()
        if not post:
            return None, []

        cursor.execute(
            "UPDATE Posts SET view_count = view_count + 1 WHERE post_id = %s",
            (post_id,),
        )
        db.commit()

        cursor.execute(
            """
            SELECT c.*, u.nickname
            FROM Comments c
            JOIN Users u ON c.user_id = u.user_id
            WHERE c.post_id = %s AND c.parent_id IS NULL
            ORDER BY c.created_at ASC
            """,
            (post_id,),
        )
        comments = cursor.fetchall()

    return post, comments


@bp.route("/")
def index():
    posts = _fetch_posts()
    return render_template("index.html", posts=posts)


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


@bp.route("/posts/<int:post_id>")
def post_detail(post_id):
    post, comments = _fetch_post(post_id)

    if post is None:
        flash("게시글을 찾을 수 없습니다.", "error")
        return redirect(url_for("main.index"))

    return render_template("post_detail.html", post=post, comments=comments)
