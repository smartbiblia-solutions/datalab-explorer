import json
import sqlite3
import uuid
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT NOT NULL, owner INTEGER NOT NULL REFERENCES users(id), active TEXT);
CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id), parent TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS objects(id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id), kind TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id), created TEXT DEFAULT CURRENT_TIMESTAMP, revoked INTEGER DEFAULT 0, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id), state TEXT NOT NULL, payload TEXT NOT NULL, result TEXT, checkpoint TEXT, updated TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS members(project TEXT REFERENCES projects(id), user INTEGER REFERENCES users(id), role TEXT CHECK(role IN ('owner','editor','viewer')), PRIMARY KEY(project,user));
"""


def uid():
    return uuid.uuid4().hex


def db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=30)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def encode(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def decode(value):
    return json.loads(value)


def insert_version(pid, rows, parent=None, recipe=None, source=None, activate=True):
    """Store an immutable dataset version. The caller commits."""
    from .data import profile

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
    if activate == "if-empty":
        db().execute(
            "UPDATE projects SET active=? WHERE id=? AND active IS NULL", (vid, pid)
        )
    elif activate:
        db().execute("UPDATE projects SET active=? WHERE id=?", (vid, pid))
    return vid
