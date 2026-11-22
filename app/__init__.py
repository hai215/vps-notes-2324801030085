import hmac
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, g, render_template, request, session
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db


def create_app(test_config=None):
    """Create and configure the Flask application."""
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-key"),
        DATABASE_URL=os.environ.get(
            "DATABASE_URL", "postgresql://localhost/vps_notes"
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get(
            "SESSION_COOKIE_SECURE", "false"
        ).lower()
        in {"1", "true", "yes"},
    )

    if test_config is not None:
        app.config.update(test_config)

    # The app is normally behind the Nginx proxy in nginx/vps-notes.conf.example.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)

    @app.before_request
    def protect_post_requests():
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        g.user = getattr(g, "user", None)
        if request.method == "POST":
            submitted = request.form.get("csrf_token", "")
            expected = session.get("csrf_token", "")
            if not expected or not hmac.compare_digest(submitted, expected):
                abort(400, description="CSRF token không hợp lệ.")

    @app.context_processor
    def inject_template_helpers():
        return {"csrf_token": session.get("csrf_token", "")}

    from . import auth, notes

    app.register_blueprint(auth.bp)
    app.register_blueprint(notes.bp)

    @app.errorhandler(400)
    def bad_request(error):
        return (
            render_template(
                "error.html",
                title="Yêu cầu không hợp lệ",
                message=getattr(error, "description", "Yêu cầu không hợp lệ."),
            ),
            400,
        )

    @app.errorhandler(404)
    def not_found(error):
        return (
            render_template(
                "error.html",
                title="Không tìm thấy",
                message="Trang bạn yêu cầu không tồn tại.",
            ),
            404,
        )

    return app
