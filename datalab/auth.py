from functools import wraps

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import db
from .i18n import translate as _

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_app.config["AUTH"] and not g.user:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@auth_bp.route("/connexion", methods=["GET", "POST"])
def login():
    if not current_app.config["AUTH"]:
        return redirect(url_for("admin.datasets"))
    if request.method == "POST":
        user = db().execute(
            "SELECT * FROM users WHERE username=?", (request.form.get("username", ""),)
        ).fetchone()
        if user and check_password_hash(user["password"], request.form.get("password", "")):
            csrf = session.get("csrf")
            session.clear()
            session["user"], session["csrf"] = user["id"], csrf
            target = request.args.get("next", "")
            return redirect(target if target.startswith("/") and not target.startswith("//") else url_for("admin.datasets"))
        flash(_("login.failed"), "danger")
    return render_template("login.html")


@auth_bp.post("/deconnexion")
def logout():
    session.clear()
    return redirect(url_for("public.home"))
