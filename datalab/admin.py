"""Curator pages: datasets, import check, view editor, publication."""

import json
import re
import secrets
import unicodedata
from pathlib import Path

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from .auth import login_required
from .db import dataset_rows, db, folder, new_id, publication_path, read_json, write_json
from .i18n import translate as _
from .tabular import SEPARATORS, TableError, describe_columns, read_table
from .views import check_slug, default_config, public_rows, validate_config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ALLOWED = (".csv", ".tsv", ".txt", ".xlsx", ".json")


@admin_bp.before_request
@login_required
def require_login():
    pass


def error_text(e):
    return _(e.key, **e.params)


def get_dataset(dataset_id):
    row = db().execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row:
        abort(404)
    return row


def get_view(view_id):
    row = db().execute(
        "SELECT v.*, d.name AS dataset_name, d.columns AS dataset_columns, d.row_count"
        " FROM views v JOIN datasets d ON d.id = v.dataset_id WHERE v.id=?", (view_id,)
    ).fetchone()
    if not row:
        abort(404)
    return row


# ---- Datasets ----

@admin_bp.get("/")
def datasets():
    items = db().execute("SELECT * FROM datasets ORDER BY updated DESC").fetchall()
    views = db().execute("SELECT * FROM views ORDER BY name").fetchall()
    by_dataset = {}
    for v in views:
        by_dataset.setdefault(v["dataset_id"], []).append(v)
    return render_template("admin/datasets.html", datasets=items, views=by_dataset)


@admin_bp.get("/donnees/<dataset_id>")
def dataset(dataset_id):
    d = get_dataset(dataset_id)
    views = db().execute("SELECT * FROM views WHERE dataset_id=? ORDER BY name", (dataset_id,)).fetchall()
    return render_template("admin/dataset.html", dataset=d, columns=json.loads(d["columns"]), views=views)


@admin_bp.get("/donnees/<dataset_id>/lignes")
def dataset_data(dataset_id):
    get_dataset(dataset_id)
    return jsonify(dataset_rows(dataset_id))


@admin_bp.post("/donnees/<dataset_id>/supprimer")
def delete_dataset(dataset_id):
    d = get_dataset(dataset_id)
    for v in db().execute("SELECT id FROM views WHERE dataset_id=?", (dataset_id,)):
        publication_path(v["id"]).unlink(missing_ok=True)
    db().execute("DELETE FROM views WHERE dataset_id=?", (dataset_id,))
    db().execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
    db().commit()
    (folder("datasets") / f"{dataset_id}.json").unlink(missing_ok=True)
    flash(_("flash.dataset_deleted", name=d["name"]), "success")
    return redirect(url_for("admin.datasets"))


# ---- Import: upload, check, save ----

@admin_bp.post("/import")
def upload():
    file = request.files.get("file")
    replace = request.form.get("replace") or ""
    if not file or not file.filename:
        flash(_("error.no_file"), "danger")
        return redirect(request.referrer or url_for("admin.datasets"))
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED:
        flash(_("error.format"), "danger")
        return redirect(request.referrer or url_for("admin.datasets"))
    if replace:
        get_dataset(replace)
    token = secrets.token_hex(8)
    uploads = folder("uploads")
    file.save(uploads / f"{token}{suffix}")
    write_json(uploads / f"{token}.meta", {"filename": Path(file.filename).name, "suffix": suffix, "replace": replace})
    return redirect(url_for("admin.check_import", token=token))


def pending(token):
    if not token.isalnum():
        abort(404)
    meta_path = folder("uploads") / f"{token}.meta"
    if not meta_path.exists():
        abort(404)
    meta = read_json(meta_path)
    return meta, folder("uploads") / f"{token}{meta['suffix']}"


def parse_options(source):
    return {k: source.get(k) for k in ("delimiter", "encoding", "sheet") if source.get(k)}


@admin_bp.get("/import/<token>")
def check_import(token):
    meta, path = pending(token)
    options = parse_options(request.args)
    table, error, described = None, None, []
    try:
        table = read_table(path.read_bytes(), meta["filename"], options)
        described = describe_columns(table["columns"], table["rows"])
    except TableError as e:
        error = error_text(e)
    replace = get_dataset(meta["replace"]) if meta["replace"] else None
    return render_template(
        "admin/import.html", token=token, meta=meta, table=table, error=error,
        described=described, options=options, separators=SEPARATORS, replace=replace,
    )


@admin_bp.post("/import/<token>")
def save_import(token):
    meta, path = pending(token)
    options = parse_options(request.form)
    try:
        table = read_table(path.read_bytes(), meta["filename"], options)
    except TableError as e:
        flash(error_text(e), "danger")
        return redirect(url_for("admin.check_import", token=token, **options))
    described = describe_columns(table["columns"], table["rows"])
    if meta["replace"]:
        dataset_id = meta["replace"]
        db().execute(
            "UPDATE datasets SET source=?, columns=?, row_count=?, updated=CURRENT_TIMESTAMP WHERE id=?",
            (meta["filename"], json.dumps(described, ensure_ascii=False), len(table["rows"]), dataset_id),
        )
        for v in db().execute("SELECT id, config FROM views WHERE dataset_id=?", (dataset_id,)).fetchall():
            config = validate_config(json.loads(v["config"]), table["columns"])
            db().execute("UPDATE views SET config=? WHERE id=?", (json.dumps(config, ensure_ascii=False), v["id"]))
        message = _("flash.dataset_replaced", rows=len(table["rows"]))
    else:
        dataset_id = new_id()
        name = (request.form.get("name") or Path(meta["filename"]).stem).strip()[:200]
        db().execute(
            "INSERT INTO datasets(id, name, source, columns, row_count) VALUES (?,?,?,?,?)",
            (dataset_id, name, meta["filename"], json.dumps(described, ensure_ascii=False), len(table["rows"])),
        )
        view_id = new_id()
        config = default_config(described, len(table["rows"]))
        db().execute(
            "INSERT INTO views(id, dataset_id, name, config) VALUES (?,?,?,?)",
            (view_id, dataset_id, name, json.dumps(config, ensure_ascii=False)),
        )
        message = _("flash.dataset_created", rows=len(table["rows"]))
    write_json(folder("datasets") / f"{dataset_id}.json", table["rows"])
    db().commit()
    path.unlink(missing_ok=True)
    (folder("uploads") / f"{token}.meta").unlink(missing_ok=True)
    flash(message, "success")
    if meta["replace"]:
        return redirect(url_for("admin.dataset", dataset_id=dataset_id))
    return redirect(url_for("admin.view_editor", view_id=view_id))


# ---- Views ----

@admin_bp.post("/donnees/<dataset_id>/vues")
def new_view(dataset_id):
    d = get_dataset(dataset_id)
    view_id = new_id()
    config = default_config(json.loads(d["columns"]), d["row_count"])
    name = (request.form.get("name") or d["name"]).strip()[:200]
    db().execute(
        "INSERT INTO views(id, dataset_id, name, config) VALUES (?,?,?,?)",
        (view_id, dataset_id, name, json.dumps(config, ensure_ascii=False)),
    )
    db().commit()
    return redirect(url_for("admin.view_editor", view_id=view_id))


@admin_bp.get("/vues/<view_id>")
def view_editor(view_id):
    v = get_view(view_id)
    described = json.loads(v["dataset_columns"])
    return render_template(
        "admin/view.html", view=v, view_config=json.loads(v["config"]), described=described,
        suggested_slug=suggest_slug(v["name"]),
    )


@admin_bp.post("/vues/<view_id>")
def save_view(view_id):
    v = get_view(view_id)
    body = request.get_json(silent=True) or {}
    columns = [c["name"] for c in json.loads(v["dataset_columns"])]
    try:
        config = validate_config(body.get("config"), columns)
    except TableError as e:
        return jsonify(error=error_text(e)), 400
    name = str(body.get("name") or v["name"]).strip()[:200]
    db().execute(
        "UPDATE views SET name=?, config=?, updated=CURRENT_TIMESTAMP WHERE id=?",
        (name, json.dumps(config, ensure_ascii=False), view_id),
    )
    db().commit()
    return jsonify(ok=True, message=_("flash.view_saved"))


@admin_bp.post("/vues/<view_id>/supprimer")
def delete_view(view_id):
    v = get_view(view_id)
    publication_path(view_id).unlink(missing_ok=True)
    db().execute("DELETE FROM views WHERE id=?", (view_id,))
    db().commit()
    flash(_("flash.view_deleted", name=v["name"]), "success")
    return redirect(url_for("admin.dataset", dataset_id=v["dataset_id"]))


def suggest_slug(name):
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:80] or "tableau"


@admin_bp.post("/vues/<view_id>/publier")
def publish(view_id):
    v = get_view(view_id)
    title = request.form.get("title", "").strip()[:200] or v["name"]
    description = request.form.get("description", "").strip()[:1000]
    try:
        slug = check_slug(request.form.get("slug"))
    except TableError as e:
        flash(error_text(e), "danger")
        return redirect(url_for("admin.view_editor", view_id=view_id))
    taken = db().execute("SELECT id FROM views WHERE slug=? AND id<>?", (slug, view_id)).fetchone()
    if taken:
        flash(_("error.slug_taken", slug=slug), "danger")
        return redirect(url_for("admin.view_editor", view_id=view_id))
    config = json.loads(v["config"])
    rows = public_rows(dataset_rows(v["dataset_id"]), config)
    write_json(publication_path(view_id), {"title": title, "description": description, "config": config, "rows": rows})
    db().execute(
        "UPDATE views SET slug=?, public_title=?, public_description=?, published_at=CURRENT_TIMESTAMP,"
        " published_rows=? WHERE id=?",
        (slug, title, description, len(rows), view_id),
    )
    db().commit()
    flash(_("flash.published", url=url_for("public.dashboard", slug=slug)), "success")
    return redirect(url_for("admin.view_editor", view_id=view_id))


@admin_bp.post("/vues/<view_id>/depublier")
def unpublish(view_id):
    get_view(view_id)
    publication_path(view_id).unlink(missing_ok=True)
    db().execute("UPDATE views SET published_at=NULL, published_rows=NULL WHERE id=?", (view_id,))
    db().commit()
    flash(_("flash.unpublished"), "success")
    return redirect(url_for("admin.view_editor", view_id=view_id))
