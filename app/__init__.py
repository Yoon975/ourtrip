from flask import Flask

from app.config import Config
from app.db import close_db
from app.error_handlers import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY

    app.teardown_appcontext(close_db)
    register_error_handlers(app)

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
    def inject_nav_counts():
        from flask import session

        counts = {"unread_messages": 0, "unread_notifications": 0}
        user_id = session.get("user_id")
        if user_id:
            try:
                from app.services.service_factory import get_message_service, get_notification_service

                counts["unread_messages"] = get_message_service().unread_count(user_id)
                counts["unread_notifications"] = get_notification_service().get_summary(user_id)["unread_count"]
            except Exception:
                pass
        return counts

    return app


def _media_url_global(path):
    from app.utils.media import media_url

    return media_url(path)
