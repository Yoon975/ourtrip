from flask import Flask, request

from app.config import Config
from app.db import close_db
from app.error_handlers import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    app.teardown_appcontext(close_db)
    register_error_handlers(app)

    @app.before_request
    def csrf_guard():
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return
        if request.endpoint == "static":
            return
        from app.utils.csrf import validate_csrf

        validate_csrf()

    from app.controllers.auth_controller import bp as auth_bp
    from app.controllers.main_controller import bp as main_bp
    from app.controllers.profile_controller import bp as profile_bp
    from app.controllers.admin_controller import bp as admin_bp
    from app.controllers.message_controller import bp as message_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(message_bp)

    app.jinja_env.globals["media_url"] = _media_url_global

    @app.context_processor
    def inject_csrf():
        from app.utils.csrf import get_csrf_token

        return {"csrf_token": get_csrf_token()}

    @app.context_processor
    def inject_nav_counts():
        from flask import session

        counts = {"unread_messages": 0, "unread_notifications": 0}
        user_id = session.get("user_id")
        if user_id:
            try:
                from app.services.service_factory import get_message_service, get_notification_service

                counts["unread_messages"] = get_message_service().unread_count(user_id)
                counts["unread_notifications"] = get_notification_service().unread_count(user_id)
            except Exception:
                pass
        return counts

    return app


def _media_url_global(path):
    from app.utils.media import media_url

    return media_url(path)
