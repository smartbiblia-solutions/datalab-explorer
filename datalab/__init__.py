import os
import secrets
from pathlib import Path

import click
from flask import Flask, abort, g, redirect, request, session
from werkzeug.security import generate_password_hash

from . import db as store
from .i18n import client_messages, current_lang, languages, translate


def create_app(test_config=None):
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        static_folder=str(root / "static"),
        template_folder=str(root / "templates"),
        instance_path=os.environ.get("DATALAB_INSTANCE", str(root / "instance")),
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or _session_key(app.instance_path),
        DATABASE=str(Path(app.instance_path) / "datalab.db"),
        MAX_CONTENT_LENGTH=64 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SITE_TITLE=os.environ.get("DATALAB_TITLE", "DataLab Explorer"),
        DEFAULT_LANG=os.environ.get("DATALAB_LANG", "fr"),
    )
    if test_config:
        app.config.update(test_config)
    with app.app_context():
        store.db().executescript(store.SCHEMA)
    app.teardown_appcontext(store.close_db)

    @app.before_request
    def load_user_and_check_csrf():
        uid = session.get("user")
        g.user = (
            store.db().execute("SELECT id, username FROM users WHERE id=?", (uid,)).fetchone()
            if uid else None
        )
        if request.method == "POST":
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
            if not secrets.compare_digest(sent, csrf_token()):
                abort(400, translate("error.csrf"))

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    app.jinja_env.globals.update(
        _=translate, csrf_token=csrf_token, current_lang=current_lang,
        languages=languages, client_messages=client_messages,
    )

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.get("/lang/<code>")
    def set_language(code):
        target = request.referrer or "/"
        response = redirect(target if target.startswith(request.host_url) else "/")
        if code in languages():
            response.set_cookie("lang", code, max_age=365 * 24 * 3600, samesite="Lax")
        return response

    @app.get("/health")
    def health():
        store.db().execute("SELECT 1")
        return {"status": "ok"}

    from .auth import auth_bp
    from .admin import admin_bp
    from .public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    @app.cli.command("add-user")
    @click.argument("username")
    @click.password_option()
    def add_user(username, password):
        """Create a curator account (the password is asked for)."""
        if len(password) < 10:
            raise click.ClickException("Use at least 10 characters.")
        store.db().execute(
            "INSERT INTO users(username, password) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        store.db().commit()
        click.echo(f"Account {username} created.")

    return app


def _session_key(instance):
    key = Path(instance) / "session.key"
    if not key.exists():
        key.write_text(secrets.token_hex(32))
        key.chmod(0o600)
    return key.read_text().strip()
