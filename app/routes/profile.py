from flask import Blueprint, abort, redirect, render_template, session, url_for

from app.db import get_db

bp = Blueprint("profile", __name__)

GENDER_LABELS = {"M": "남성", "F": "여성", "U": "미선택"}


def _fetch_profile(user_id):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return None

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Posts WHERE user_id = %s", (user_id,)
        )
        post_count = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Scraps WHERE user_id = %s", (user_id,)
        )
        scrap_count = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Comments WHERE user_id = %s", (user_id,)
        )
        comment_count = cursor.fetchone()["cnt"]

        cursor.execute(
            """
            SELECT COUNT(DISTINCT location_country) AS cnt
            FROM Posts WHERE user_id = %s
            """,
            (user_id,),
        )
        country_count = cursor.fetchone()["cnt"]

        cursor.execute(
            """
            SELECT DISTINCT location_country
            FROM Posts WHERE user_id = %s
            ORDER BY location_country
            LIMIT 5
            """,
            (user_id,),
        )
        countries = [row["location_country"] for row in cursor.fetchall()]

        cursor.execute(
            """
            SELECT title FROM Posts
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 3
            """,
            (user_id,),
        )
        recent_posts = cursor.fetchall()

    stats = {
        "post_count": post_count,
        "scrap_count": scrap_count,
        "comment_count": comment_count,
        "country_count": country_count,
    }
    return user, stats, countries, recent_posts


@bp.route("/profile")
def my_profile():
    user_id = session.get("user_id", 1)
    return redirect(url_for("profile.view_profile", user_id=user_id))


@bp.route("/profile/<int:user_id>")
def view_profile(user_id):
    result = _fetch_profile(user_id)
    if result is None:
        abort(404)

    user, stats, countries, recent_posts = result
    gender_label = GENDER_LABELS.get(user.get("gender", "U"), "미선택")

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        countries=countries,
        recent_posts=recent_posts,
        gender_label=gender_label,
    )
