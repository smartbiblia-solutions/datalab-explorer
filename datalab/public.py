"""Public pages: the catalogue of published dashboards and each dashboard."""

from flask import Blueprint, abort, jsonify, render_template

from .db import db, publication_path, read_json

public_bp = Blueprint("public", __name__)


def published(slug):
    view = db().execute(
        "SELECT * FROM views WHERE slug=? AND published_at IS NOT NULL", (slug,)
    ).fetchone()
    if not view or not publication_path(view["id"]).exists():
        abort(404)
    return view


@public_bp.get("/")
def home():
    views = db().execute(
        "SELECT * FROM views WHERE published_at IS NOT NULL ORDER BY published_at DESC"
    ).fetchall()
    return render_template("home.html", views=views)


@public_bp.get("/v/<slug>")
def dashboard(slug):
    return render_template("dashboard.html", view=published(slug))


@public_bp.get("/v/<slug>/donnees")
def dashboard_data(slug):
    publication = read_json(publication_path(published(slug)["id"]))
    return jsonify(config=publication["config"], rows=publication["rows"])
