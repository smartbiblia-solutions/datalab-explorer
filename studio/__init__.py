import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
import uuid
import click
from flask import (
    Flask,
    abort,
    g,
    jsonify,
    render_template,
    request,
    session,
    send_from_directory,
)
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from .db import db, migrate, encode, decode
from .data import parse_upload, profile, prepare, validate_fields, dashboard, normalize


def uid():
    return uuid.uuid4().hex


def create_app(test_config=None):
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        static_folder=str(root / "static"),
        template_folder=str(root / "templates"),
        instance_path=os.environ.get("DATALAB_INSTANCE", str(root / "instance")),
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    key = Path(app.instance_path) / "session.key"
    if not key.exists():
        try:
            with key.open("x") as f:
                f.write(secrets.token_hex(32))
            key.chmod(0o600)
        except FileExistsError:
            pass
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or key.read_text(),
        DATABASE=str(Path(app.instance_path) / "studio.db"),
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    with app.app_context():
        connection = db()
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 2:
            raise RuntimeError("Database schema is newer than this application")
        migrate(connection)

    @app.teardown_appcontext
    def close(_):
        conn = g.pop("db", None)
        if conn:
            conn.close()

    @app.before_request
    def auth():
        g.user = (
            db()
            .execute("SELECT id,username FROM users WHERE id=?", (session.get("user"),))
            .fetchone()
            if session.get("user")
            else None
        )
        if (
            request.path.startswith("/api/")
            and request.path not in ("/api/session", "/api/login")
            and not g.user
        ):
            abort(401)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            expected = session.get("csrf")
            if not expected or not secrets.compare_digest(
                request.headers.get("X-CSRF-Token", ""), expected
            ):
                abort(403, "Invalid CSRF token")

    @app.errorhandler(Exception)
    def error(e):
        if isinstance(e, HTTPException):
            return jsonify(error=e.description), e.code
        if isinstance(
            e, (ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError)
        ):
            return jsonify(error=str(e)), 400
        if isinstance(e, sqlite3.IntegrityError):
            return jsonify(error="Conflicting or invalid record"), 409
        app.logger.exception("Request failed")
        return jsonify(error="Internal server error"), 500

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith(("/api/", "/public/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(
            status="ok",
            schema=db().execute("PRAGMA user_version").fetchone()[0],
            build=(root / "static/dist/manifest.json").exists(),
        )

    @app.get("/vendor/<path:filename>")
    def vendor(filename):
        return send_from_directory(root / "vendor/keshif", filename)

    @app.get("/api/session")
    def who():
        session.setdefault("csrf", secrets.token_hex(32))
        return jsonify(user=dict(g.user) if g.user else None, csrf=session["csrf"])

    @app.post("/api/login")
    def login():
        body = request.get_json()
        user = (
            db()
            .execute("SELECT * FROM users WHERE username=?", (body.get("username"),))
            .fetchone()
        )
        if not user or not check_password_hash(
            user["password"], body.get("password", "")
        ):
            abort(401, "Invalid credentials")
        session.clear()
        session["user"] = user["id"]
        session["csrf"] = secrets.token_hex(32)
        return jsonify(
            user={"id": user["id"], "username": user["username"]}, csrf=session["csrf"]
        )

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.cli.command("add-user")
    @click.argument("username")
    @click.password_option()
    def add_user(username, password):
        if len(password) < 10:
            raise click.ClickException("Use at least 10 characters")
        db().execute(
            "INSERT INTO users(username,password) VALUES (?,?)",
            (username, generate_password_hash(password)),
        )
        db().commit()
        click.echo("Account created")

    @app.cli.command("worker")
    @click.option("--once", is_flag=True)
    def worker(once):
        from .jobs import run_worker

        run_worker(once)

    def project(pid, level="viewer"):
        p = (
            db()
            .execute(
                "SELECT p.*,m.role FROM projects p JOIN members m ON p.id=m.project WHERE p.id=? AND m.user=?",
                (pid, g.user["id"]),
            )
            .fetchone()
        )
        if not p:
            abort(404)
        if {"viewer": 0, "editor": 1, "owner": 2}[p["role"]] < {
            "viewer": 0,
            "editor": 1,
            "owner": 2,
        }[level]:
            abort(403)
        return p

    def version(pid, vid=None):
        p = project(pid)
        v = (
            db()
            .execute(
                "SELECT * FROM versions WHERE project=? AND id=?",
                (pid, vid or p["active"]),
            )
            .fetchone()
        )
        if not v:
            abort(404, "Import a dataset first")
        return v, decode(v["payload"])

    def save_version(pid, rows, parent=None, recipe=None, source=None):
        vid = uid()
        payload = {
            "rows": rows,
            "fields": profile(rows),
            "recipe": recipe or [],
            "source": source or {},
        }
        db().execute(
            "INSERT INTO versions(id,project,parent,payload) VALUES (?,?,?,?)",
            (vid, pid, parent, encode(payload)),
        )
        db().execute("UPDATE projects SET active=? WHERE id=?", (vid, pid))
        db().commit()
        return vid

    @app.route("/api/projects", methods=["GET", "POST"])
    def projects():
        if request.method == "GET":
            return jsonify(
                [
                    dict(r)
                    for r in db().execute(
                        "SELECT p.*,m.role FROM projects p JOIN members m ON p.id=m.project WHERE m.user=? ORDER BY p.rowid DESC",
                        (g.user["id"],),
                    )
                ]
            )
        name = request.get_json().get("name", "").strip()
        if not name or len(name) > 200:
            raise ValueError("Project name required (max 200)")
        pid = uid()
        db().execute(
            "INSERT INTO projects(id,name,owner) VALUES (?,?,?)",
            (pid, name, g.user["id"]),
        )
        db().execute("INSERT INTO members VALUES (?,?,?)", (pid, g.user["id"], "owner"))
        db().commit()
        return jsonify(id=pid), 201

    @app.get("/api/projects/<pid>")
    def get_project(pid):
        p = project(pid)
        versions = [
            dict(v)
            for v in db().execute(
                "SELECT id,parent,created FROM versions WHERE project=? ORDER BY rowid DESC",
                (pid,),
            )
        ]
        objects = [
            dict(o, payload=decode(o["payload"]))
            for o in db().execute("SELECT * FROM objects WHERE project=?", (pid,))
        ]
        releases = [
            dict(r)
            for r in db().execute(
                "SELECT id,created,revoked FROM releases WHERE project=?", (pid,)
            )
        ]
        return jsonify(
            project=dict(p), versions=versions, objects=objects, releases=releases
        )

    @app.route("/api/projects/<pid>/members", methods=["GET", "POST"])
    def members(pid):
        project(pid, "owner" if request.method == "POST" else "viewer")
        if request.method == "GET":
            return jsonify(
                [
                    dict(r)
                    for r in db().execute(
                        "SELECT u.username,m.role FROM members m JOIN users u ON m.user=u.id WHERE m.project=?",
                        (pid,),
                    )
                ]
            )
        b = request.get_json()
        u = (
            db()
            .execute("SELECT id FROM users WHERE username=?", (b.get("username"),))
            .fetchone()
        )
        if not u:
            raise ValueError("Account does not exist; create it with the account CLI")
        existing = (
            db()
            .execute(
                "SELECT role FROM members WHERE project=? AND user=?", (pid, u["id"])
            )
            .fetchone()
        )
        if existing and existing["role"] == "owner":
            abort(400, "Owner cannot be removed or downgraded")
        role = b.get("role")
        if role not in ("editor", "viewer", "remove"):
            raise ValueError("Choose editor, viewer or remove")
        db().execute("DELETE FROM members WHERE project=? AND user=?", (pid, u["id"]))
        if role != "remove":
            db().execute("INSERT INTO members VALUES (?,?,?)", (pid, u["id"], role))
        db().commit()
        return jsonify(ok=True)

    @app.post("/api/projects/<pid>/imports")
    def upload(pid):
        project(pid, "editor")
        f = request.files.get("file")
        if not f:
            raise ValueError("Choose a file")
        blob = f.read()
        options = json.loads(request.form.get("options", "{}"))
        rows = parse_upload(blob, f.filename or "", options)
        # Retain originals only under generated managed names, never user paths.
        raw = Path(app.instance_path) / "raw"
        raw.mkdir(exist_ok=True)
        raw_id = uid()
        (raw / raw_id).write_bytes(blob)
        vid = save_version(
            pid,
            rows,
            source={
                "kind": "file",
                "name": Path(f.filename).name,
                "raw": raw_id,
                "options": options,
            },
        )
        return jsonify(id=vid, rows=len(rows)), 201

    @app.get("/api/projects/<pid>/versions/<vid>")
    def get_version(pid, vid):
        v, payload = version(pid, vid)
        return jsonify(id=vid, parent=v["parent"], **payload)

    @app.post("/api/projects/<pid>/activate")
    def activate(pid):
        project(pid, "editor")
        vid = request.get_json()["version"]
        version(pid, vid)
        db().execute("UPDATE projects SET active=? WHERE id=?", (vid, pid))
        db().commit()
        return jsonify(ok=True)

    @app.post("/api/projects/<pid>/prepare")
    def preparation(pid):
        project(pid, "editor")
        b = request.get_json()
        v, payload = version(pid, b.get("version"))
        rows, errors = prepare(payload["rows"], b.get("steps"))
        if b.get("preview", False) or errors:
            return jsonify(
                rows=rows[:20], count=len(rows), fields=profile(rows), errors=errors
            ), 422 if errors else 200
        vid = save_version(
            pid, rows, v["id"], payload["recipe"] + b["steps"], payload["source"]
        )
        return jsonify(id=vid), 201

    @app.route("/api/projects/<pid>/objects", methods=["POST"])
    def save_object(pid):
        project(pid, "editor")
        b = request.get_json()
        kind = b.get("kind")
        value = b.get("payload")
        if kind not in ("dictionary", "dashboard", "snapshot", "cohort", "recipe"):
            raise ValueError("Unknown object kind")
        if not isinstance(value, dict):
            raise ValueError("Object payload required")
        vid = value.get("version")
        v, payload = version(pid, vid)
        if kind == "dictionary":
            value = {
                "version": v["id"],
                "fields": validate_fields(value["fields"], payload["rows"]),
            }
        if kind == "dashboard":
            value = {"version": v["id"], **dashboard(value, payload["fields"])}
        if kind in ("cohort", "snapshot"):
            valid = {r["__id"] for r in payload["rows"]}
            ids = value.get("ids")
            if not isinstance(ids, list) or any(i not in valid for i in ids):
                raise ValueError("Selection must contain exact IDs from this version")
            value = {
                k: value[k]
                for k in (
                    "name",
                    "note",
                    "ids",
                    "filters",
                    "table",
                    "dashboard",
                    "version",
                )
                if k in value
            }
            value["version"] = v["id"]
        oid = b.get("id") or uid()
        existing = (
            db()
            .execute("SELECT project,kind FROM objects WHERE id=?", (oid,))
            .fetchone()
        )
        if existing and (existing["project"] != pid or existing["kind"] != kind):
            abort(404)
        db().execute(
            "INSERT INTO objects(id,project,kind,payload) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
            (oid, pid, kind, encode(value)),
        )
        db().commit()
        return jsonify(id=oid), 201

    @app.get("/api/projects/<pid>/diff")
    def diff(pid):
        _, a = version(pid, request.args["a"])
        _, b = version(pid, request.args["b"])
        ra = {r["__id"]: r for r in a["rows"]}
        rb = {r["__id"]: r for r in b["rows"]}
        ka = {f["id"] for f in a["fields"]}
        kb = {f["id"] for f in b["fields"]}
        return jsonify(
            added=sorted(rb.keys() - ra.keys()),
            removed=sorted(ra.keys() - rb.keys()),
            changed=sorted(k for k in ra.keys() & rb.keys() if ra[k] != rb[k]),
            new_fields=sorted(kb - ka),
            removed_fields=sorted(ka - kb),
            identity_note="Generated IDs are version-local; cross-refresh comparisons require a natural identity",
        )

    def portable(pid):
        project(pid)
        versions = []
        for v in db().execute("SELECT * FROM versions WHERE project=?", (pid,)):
            p = decode(v["payload"])
            p["source"] = {"kind": p["source"].get("kind", "unknown")}
            versions.append({"id": v["id"], "parent": v["parent"], "payload": p})
        objects = [
            {"id": o["id"], "kind": o["kind"], "payload": decode(o["payload"])}
            for o in db().execute("SELECT * FROM objects WHERE project=?", (pid,))
        ]
        p = project(pid)
        return {
            "format": "datalab-project",
            "schema": 2,
            "name": p["name"],
            "active": p["active"],
            "versions": versions,
            "objects": objects,
        }

    @app.get("/api/projects/<pid>/export")
    def export_project(pid):
        return jsonify(portable(pid))

    @app.post("/api/project-import")
    def import_project():
        b = request.get_json()
        if b.get("format") != "datalab-project" or b.get("schema") != 2:
            raise ValueError("Unsupported project manifest")
        # Validate completely before writing anything; never execute imported callbacks.
        clean = []
        mapping = {}
        for v in b["versions"]:
            oldrows = v["payload"]["rows"]
            rows = normalize(
                [{k: val for k, val in r.items() if k != "__id"} for r in oldrows]
            )
            ids = [r["__id"] for r in oldrows]
            if len(set(ids)) != len(ids) or any(
                not isinstance(i, str) or not i for i in ids
            ):
                raise ValueError("Invalid IDs")
            for r, i in zip(rows, ids):
                r["__id"] = i
            fields = validate_fields(v["payload"]["fields"], rows)
            clean.append((v, rows, fields))
            mapping[v["id"]] = uid()
        if b["active"] not in mapping:
            raise ValueError("Unknown active version")
        allowed = {"dictionary", "dashboard", "snapshot", "cohort", "recipe"}
        for o in b["objects"]:
            p = o["payload"]
            old = p.get("version")
            if o["kind"] not in allowed or old not in mapping:
                raise ValueError("Invalid object/version")
            rows = next(rows for v, rows, fields in clean if v["id"] == old)
            fields = profile(rows)
            if o["kind"] == "dashboard":
                dashboard(p, fields)
            if o["kind"] == "dictionary":
                validate_fields(p["fields"], rows)
            if o["kind"] in ("snapshot", "cohort") and any(
                i not in {r["__id"] for r in rows} for i in p["ids"]
            ):
                raise ValueError("Unknown cohort ID")
        pid = uid()
        db().execute(
            "INSERT INTO projects(id,name,owner,active) VALUES (?,?,?,?)",
            (pid, str(b["name"])[:200], g.user["id"], mapping[b["active"]]),
        )
        db().execute("INSERT INTO members VALUES (?,?,?)", (pid, g.user["id"], "owner"))
        for v, rows, fields in clean:
            db().execute(
                "INSERT INTO versions(id,project,parent,payload) VALUES (?,?,?,?)",
                (
                    mapping[v["id"]],
                    pid,
                    mapping.get(v["parent"]),
                    encode(
                        {
                            "rows": rows,
                            "fields": fields,
                            "recipe": v["payload"].get("recipe", []),
                            "source": {"kind": "manifest"},
                        }
                    ),
                ),
            )
        for o in b["objects"]:
            p = dict(o["payload"])
            p["version"] = mapping[p["version"]]
            db().execute(
                "INSERT INTO objects VALUES (?,?,?,?)",
                (uid(), pid, o["kind"], encode(p)),
            )
        db().commit()
        return jsonify(id=pid), 201

    @app.post("/api/projects/<pid>/selection-export")
    def selection_export(pid):
        b = request.get_json()
        _, p = version(pid, b.get("version"))
        ids = b.get("ids")
        if not isinstance(ids, list):
            raise ValueError("Exact selection IDs required; [] means empty")
        wanted = set(ids)
        return jsonify([r for r in p["rows"] if r["__id"] in wanted])

    def publication(pid, b):
        v, p = version(pid, b.get("version"))
        keys = b.get("fields", [])
        valid = {f["id"] for f in p["fields"]}
        if not keys or len(set(keys)) != len(keys) or any(k not in valid for k in keys):
            raise ValueError("Choose a public field allowlist")
        # Never reuse private IDs: even stable IDs can themselves disclose information.
        rows = [
            {**{k: r[k] for k in keys if k in r}, "__id": str(i)}
            for i, r in enumerate(p["rows"])
        ]
        fields = profile(rows)
        d = dashboard(b.get("dashboard", {}), fields)
        return {
            "schema": 1,
            "title": str(b.get("title", "Dataset"))[:200],
            "rows": rows,
            "fields": fields,
            "dashboard": d,
            "data_date": v["created"],
        }

    @app.post("/api/projects/<pid>/publication-preview")
    def preview(pid):
        project(pid, "owner")
        p = publication(pid, request.get_json())
        digest = hashlib.sha256(encode(p).encode()).hexdigest()
        session["review"] = {"pid": pid, "digest": digest}
        return jsonify(preview=p, digest=digest)

    @app.post("/api/projects/<pid>/releases")
    def publish(pid):
        project(pid, "owner")
        b = request.get_json()
        p = publication(pid, b)
        digest = hashlib.sha256(encode(p).encode()).hexdigest()
        if (
            b.get("confirmed") is not True
            or b.get("digest") != digest
            or session.get("review") != {"pid": pid, "digest": digest}
        ):
            abort(409, "Review is stale; preview the exact public projection again")
        rid = uid()
        db().execute(
            "INSERT INTO releases(id,project,payload) VALUES (?,?,?)",
            (rid, pid, encode(p)),
        )
        db().commit()
        session.pop("review", None)
        return jsonify(id=rid, url="/public/" + rid), 201

    @app.post("/api/projects/<pid>/releases/<rid>/revoke")
    def revoke(pid, rid):
        project(pid, "owner")
        db().execute(
            "UPDATE releases SET revoked=1 WHERE id=? AND project=?", (rid, pid)
        )
        db().commit()
        return jsonify(ok=True)

    def release(rid):
        r = (
            db()
            .execute("SELECT payload FROM releases WHERE id=? AND revoked=0", (rid,))
            .fetchone()
        )
        if not r:
            abort(404)
        return decode(r["payload"])

    @app.get("/public/<rid>")
    def public_page(rid):
        release(rid)
        return render_template("index.html", public_id=rid)

    @app.get("/public/<rid>/data")
    def public_data(rid):
        return jsonify(release(rid))

    @app.get("/public/<rid>/export")
    def public_export(rid):
        return jsonify(release(rid)["rows"])

    @app.post("/api/projects/<pid>/jobs")
    def enqueue(pid):
        project(pid, "editor")
        from .jobs import validate_source

        b = validate_source(request.get_json())
        jid = uid()
        db().execute(
            "INSERT INTO jobs(id,project,state,payload) VALUES (?,?,?,?)",
            (jid, pid, "queued", encode(b)),
        )
        db().commit()
        return jsonify(id=jid), 202

    @app.get("/api/projects/<pid>/jobs")
    def jobs(pid):
        project(pid)
        return jsonify(
            [
                dict(r, checkpoint=decode(r["checkpoint"]) if r["checkpoint"] else None)
                for r in db().execute(
                    "SELECT id,state,result,checkpoint,updated FROM jobs WHERE project=? ORDER BY rowid DESC",
                    (pid,),
                )
            ]
        )

    @app.post("/api/projects/<pid>/jobs/<jid>/cancel")
    def cancel(pid, jid):
        project(pid, "editor")
        db().execute(
            "UPDATE jobs SET state='cancelled' WHERE id=? AND project=? AND state IN ('queued','running')",
            (jid, pid),
        )
        db().commit()
        return jsonify(ok=True)

    @app.post("/api/projects/<pid>/jobs/<jid>/retry")
    def retry(pid, jid):
        project(pid, "editor")
        r = (
            db()
            .execute("SELECT * FROM jobs WHERE id=? AND project=?", (jid, pid))
            .fetchone()
        )
        if not r:
            abort(404)
        if r["state"] not in ("failed", "cancelled"):
            abort(409)
        # Restart is explicit: mutable APIs do not promise consistent resumption.
        db().execute(
            "UPDATE jobs SET state='queued',checkpoint=NULL,result=NULL WHERE id=?",
            (jid,),
        )
        db().commit()
        return jsonify(ok=True, restarted=True)

    return app
