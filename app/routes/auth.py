from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db

bp = Blueprint("auth", __name__)


def _parse_birth_year(value):
    if not value:
        return None
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return None


def _create_user(email, password, nickname, birth_year=None, gender="U"):
    db = get_db()
    hashed = generate_password_hash(password)
    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Users (email, password, nickname, gender, birth_year)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (email, hashed, nickname, gender, birth_year),
        )
    db.commit()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT user_id, nickname, password FROM Users WHERE email = %s",
                (email,),
            )
            user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["nickname"] = user["nickname"]
            flash(f"{user['nickname']}님, 환영합니다!", "success")
            return redirect(url_for("main.index"))

        flash("이메일 또는 비밀번호가 올바르지 않습니다.", "error")

    return render_template("login.html")


@bp.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@bp.route("/api/user/create", methods=["POST"])
def api_create_user():
    data = request.get_json(silent=True) or {}

    email = (data.get("u_id") or data.get("email") or "").strip()
    password = data.get("pw") or data.get("password") or ""
    nickname = (data.get("nick") or data.get("nickname") or "").strip()
    birth_year = _parse_birth_year(data.get("birth_year") or data.get("address"))

    if not email or not password or not nickname:
        return jsonify(
            {"success": False, "message": "필수 항목을 모두 입력해 주세요."}
        ), 400

    try:
        _create_user(email, password, nickname, birth_year)
        return jsonify(
            {
                "success": True,
                "message": "회원가입이 완료되었습니다!",
                "redirect": url_for("auth.login"),
            }
        )
    except Exception as exc:
        if "Duplicate" in str(exc):
            return jsonify(
                {"success": False, "message": "이미 사용 중인 이메일 또는 닉네임입니다."}
            ), 409
        return jsonify(
            {"success": False, "message": "회원가입 처리 중 오류가 발생했습니다."}
        ), 500


@bp.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("main.index"))
