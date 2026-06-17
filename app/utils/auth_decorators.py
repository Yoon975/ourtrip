from functools import wraps

from flask import flash, jsonify, redirect, session, url_for


def _is_admin():
    return session.get("role") == "admin"


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("로그인이 필요합니다.", "error")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapper


def api_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401
        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("로그인이 필요합니다.", "error")
            return redirect(url_for("auth.login"))
        if not _is_admin():
            flash("관리자만 접근할 수 있습니다.", "error")
            return redirect(url_for("main.index"))
        return view_func(*args, **kwargs)

    return wrapper


def api_admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401
        if not _is_admin():
            return jsonify({"success": False, "message": "관리자만 접근할 수 있습니다."}), 403
        return view_func(*args, **kwargs)

    return wrapper
