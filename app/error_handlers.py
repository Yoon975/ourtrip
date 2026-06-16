from flask import flash, jsonify, render_template, request
import pymysql

from app.exceptions import AppException


def register_error_handlers(app):
    @app.errorhandler(pymysql.err.OperationalError)
    def handle_db_operational_error(error):
        message = (
            "데이터베이스에 연결할 수 없습니다. "
            "MySQL 실행 여부와 .env의 DB_HOST, DB_USER, DB_PASSWORD, DB_NAME 설정을 확인하세요."
        )
        app.logger.error("DB connection error: %s", error)
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": message}), 503
        flash(message, "error")
        return render_template("errors/error.html", message=message), 503

    @app.errorhandler(AppException)
    def handle_app_exception(error):
        if request.path.startswith("/api/"):
            payload = {"success": False, "message": error.message}
            if getattr(error, "errors", None):
                payload["errors"] = error.errors
            return jsonify(payload), error.status_code

        flash(error.message, "error")
        return render_template("errors/error.html", message=error.message), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "요청한 API를 찾을 수 없습니다."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_server_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "서버 내부 오류가 발생했습니다."}), 500
        return render_template("errors/500.html"), 500
