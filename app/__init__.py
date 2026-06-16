from flask import Flask

from app.db import close_db


def create_app():
    app = Flask(__name__)
    app.secret_key = "our-trip-dev-secret"

    app.teardown_appcontext(close_db)

    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.profile import bp as profile_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)

    return app
