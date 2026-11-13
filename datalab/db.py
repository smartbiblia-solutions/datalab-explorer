"""SQLite storage. Dataset rows and published copies are JSON files in the instance folder."""

import json
import os
import sqlite3
import uuid
from pathlib import Path
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS datasets(
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source TEXT NOT NULL,
  columns TEXT NOT NULL,
  row_count INTEGER NOT NULL,
  created TEXT DEFAULT CURRENT_TIMESTAMP,
  updated TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS views(
  id TEXT PRIMARY KEY,
  dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  config TEXT NOT NULL,
  updated TEXT DEFAULT CURRENT_TIMESTAMP,
  slug TEXT UNIQUE,
  public_title TEXT,
  public_description TEXT,
  published_at TEXT,
  published_rows INTEGER);
"""


def new_id():
    return uuid.uuid4().hex[:12]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=30)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(_=None):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def folder(name):
    path = Path(current_app.instance_path) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dataset_rows(dataset_id):
    return read_json(folder("datasets") / f"{dataset_id}.json")


def publication_path(view_id):
    return folder("publications") / f"{view_id}.json"
