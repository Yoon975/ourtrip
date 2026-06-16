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

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)

    app.jinja_env.globals["media_url"] = _media_url_global

    return app


def _media_url_global(path):
    from app.utils.media import media_url

    return media_url(path)
