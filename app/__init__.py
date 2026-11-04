import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .db import close_db, init_db, Base, db
from .errors import ApiError, utc_now
from .routes import bp
from .security import RateLimiter


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        DATABASE=os.environ.get("SGCM_DATABASE", "sgcm.db"),
        JWT_SECRET=os.environ.get("SGCM_JWT_SECRET"),  # never hard-coded
        JWT_TTL_MINUTES=15,
        MAX_CONTENT_LENGTH=16 * 1024,  # API4: cap request size
        LOGIN_MAX_FAILURES=5,
        LOGIN_WINDOW_SECONDS=300,
        CLOCK=utc_now,
    )
    if config:
        app.config.update(config)
    secret = app.config["JWT_SECRET"]
    if not secret or len(secret) < 32:
        raise RuntimeError("SGCM_JWT_SECRET must be set (>= 32 characters)")

    app.extensions["login_limiter"] = RateLimiter(
        app.config["LOGIN_MAX_FAILURES"], app.config["LOGIN_WINDOW_SECONDS"])
    app.teardown_appcontext(close_db)
    app.register_blueprint(bp)
    with app.app_context():
        init_db()

    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify(error=err.message), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify(error=err.name), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(_err):
        app.logger.exception("Unhandled error")
        return jsonify(error="Internal server error"), 500

    @app.after_request
    def security_headers(resp):  # API8: security misconfiguration
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        resp.headers.pop("Server", None)
        return resp

    return app