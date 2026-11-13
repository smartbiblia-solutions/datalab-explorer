"""Bounded GET-only worker with durable checkpoints and explicit restart semantics."""

import ipaddress
import os
from pathlib import Path
import re
import socket
import time
from urllib.parse import urljoin, urlsplit, parse_qs
import requests
from flask import current_app
from .data import normalize, path_get, profile
from .db import db, encode, decode
import uuid


def validate_url(url):
    p = urlsplit(url)
    allowed = set(
        current_app.config.get("API_HOSTS")
        or os.environ.get("DATALAB_API_HOSTS", "api.openalex.org").split(",")
    )
    if (
        p.scheme != "https"
        or not p.hostname
        or p.username
        or p.password
        or p.port not in (None, 443)
        or p.hostname not in allowed
    ):
        raise ValueError("Use HTTPS on a server-approved API host (DATALAB_API_HOSTS)")
    if p.hostname in ("localhost", "metadata.google.internal") or p.hostname.endswith(
        (".local", ".internal")
    ):
        raise ValueError("Internal destinations are forbidden")
    try:
        addresses = {
            a[4][0]
            for a in socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror:
        # The platform HTTPS proxy can resolve public names unavailable to local DNS.
        # Exact server-managed allowlisting remains mandatory in that environment.
        addresses = set()
    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise ValueError("Non-public destination forbidden")
    if any(
        k.lower()
        in {"api_key", "apikey", "token", "access_token", "password", "secret", "key"}
        for k in parse_qs(p.query)
    ):
        raise ValueError(
            "Use a server-side credential reference; secrets in URLs are not supported"
        )
    return url


def validate_source(b):
    if not isinstance(b, dict):
        raise ValueError("Source object required")
    url = validate_url(b.get("url", ""))
    mode = b.get("pagination", "none")
    if mode not in ("none", "page", "offset", "cursor", "next"):
        raise ValueError("Unsupported pagination")
    result = {
        "url": url,
        "pagination": mode,
        "records_path": str(b.get("records_path", "results")),
        "max_pages": int(b.get("max_pages", 5)),
        "max_records": int(b.get("max_records", 1000)),
        "page_size": int(b.get("page_size", 100)),
        "identity": b.get("identity") or None,
        "parameter": str(
            b.get(
                "parameter",
                {"page": "page", "offset": "offset", "cursor": "cursor"}.get(mode, ""),
            )
        ),
        "next_path": str(b.get("next_path", "meta.next_cursor")),
    }
    if (
        not 1 <= result["max_pages"] <= 100
        or not 1 <= result["max_records"] <= 30000
        or not 1 <= result["page_size"] <= 200
    ):
        raise ValueError("Import limits out of range")
    if b.get("secret_ref"):
        if not re.fullmatch(r"DATALAB_[A-Z0-9_]+", b["secret_ref"]):
            raise ValueError("Secret reference must name a DATALAB_ variable")
        result["secret_ref"] = b["secret_ref"]
    return result


def fetch_page(url, params, headers):
    for redirect in range(6):
        validate_url(url)
        for attempt in range(3):
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=(10, 30),
                allow_redirects=False,
                stream=True,
            )
            if response.status_code in (429, 502, 503, 504) and attempt < 2:
                delay = response.headers.get("Retry-After", "1")
                delay = int(delay) if delay.isdigit() else 1
                if delay > 10:
                    raise ValueError(
                        "Server requested a longer pause; restart import later"
                    )
                response.close()
                time.sleep(delay)
                continue
            break
        if response.is_redirect:
            target = urljoin(url, response.headers.get("Location", ""))
            if urlsplit(target).hostname != urlsplit(url).hostname:
                headers = {}  # never forward authorization across hosts
            response.close()
            url = validate_url(target)
            params = {}
            continue
        response.raise_for_status()
        content = bytearray()
        try:
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > 8 * 1024 * 1024:
                    raise ValueError("API page exceeds 8 MiB")
        finally:
            response.close()
        return __import__("json").loads(content)
    raise ValueError("Too many redirects")


def process_job(job):
    jid, pid = job["id"], job["project"]
    source = decode(job["payload"])
    rows = []
    cursor = "*"
    url = source["url"]
    start = time.monotonic()
    seen = set()
    headers = {}
    if source.get("secret_ref"):
        credential = os.environ.get(source["secret_ref"])
        if not credential:
            raise ValueError("Configured credential reference is unavailable")
        headers = {"Authorization": "Bearer " + credential}
    rawdir = Path(current_app.instance_path) / "jobs" / jid
    rawdir.mkdir(parents=True, exist_ok=True)
    for page in range(source["max_pages"]):
        if time.monotonic() - start > 120:
            raise ValueError("Import exceeded 120 seconds")
        state = (
            db()
            .execute("SELECT state FROM jobs WHERE id=?", (jid,))
            .fetchone()["state"]
        )
        if state == "cancelled":
            return
        params = {}
        mode = source["pagination"]
        if mode in ("page", "offset", "cursor"):
            params[source["parameter"]] = (
                page + 1
                if mode == "page"
                else page * source["page_size"]
                if mode == "offset"
                else cursor
            )
            params["per_page"] = source["page_size"]
        payload = fetch_page(url, params, headers)
        records = path_get(payload, source["records_path"])
        if not isinstance(records, list) or any(
            not isinstance(r, dict) for r in records
        ):
            raise ValueError("Records path must resolve to an object array")
        (rawdir / f"{page}.json").write_text(encode(payload))
        if len(rows) + len(records) > source["max_records"]:
            raise ValueError(
                "Record limit exceeded; use a narrower query (no silent truncation)"
            )
        rows.extend(records)
        checkpoint = {"pages": page + 1, "records": len(rows), "restart_only": True}
        db().execute(
            "UPDATE jobs SET checkpoint=?,updated=CURRENT_TIMESTAMP WHERE id=?",
            (encode(checkpoint), jid),
        )
        db().commit()
        if mode == "none" or not records:
            break
        if mode in ("cursor", "next"):
            nxt = path_get(payload, source["next_path"])
            if not nxt:
                break
            if str(nxt) in seen:
                raise ValueError("Pagination repeated a cursor or URL")
            seen.add(str(nxt))
            if mode == "cursor":
                cursor = nxt
            else:
                url = validate_url(urljoin(url, str(nxt)))
        elif len(records) < source["page_size"]:
            break
    else:
        raise ValueError(
            "Page limit reached before exhaustion; narrow the query or raise the limit"
        )
    normalized = normalize(rows, source.get("identity"))
    vid = uuid.uuid4().hex
    payload = {
        "rows": normalized,
        "fields": profile(normalized),
        "recipe": [],
        "source": {
            "kind": "api",
            "definition": {k: v for k, v in source.items() if k != "secret_ref"},
        },
    }
    # Serialized transaction makes cancellation atomic with final publication of a version.
    db().execute("BEGIN IMMEDIATE")
    if (
        db().execute("SELECT state FROM jobs WHERE id=?", (jid,)).fetchone()["state"]
        == "cancelled"
    ):
        db().rollback()
        return
    db().execute(
        "INSERT INTO versions(id,project,payload) VALUES (?,?,?)",
        (vid, pid, encode(payload)),
    )
    # Refresh rehearsal: do not promote a refresh automatically.
    db().execute(
        "UPDATE projects SET active=? WHERE id=? AND active IS NULL", (vid, pid)
    )
    db().execute(
        "UPDATE jobs SET state='succeeded',result=?,updated=CURRENT_TIMESTAMP WHERE id=?",
        (vid, jid),
    )
    db().commit()


def run_worker(once=False):
    # A single worker is supported. On restart stale interrupted jobs are diagnosed,
    # never silently replayed against a changing remote source.
    db().execute(
        "UPDATE jobs SET state='failed',result='Worker interrupted; explicitly restart import' WHERE state='running' AND updated < datetime('now','-5 minutes')"
    )
    db().commit()
    while True:
        db().execute("BEGIN IMMEDIATE")
        job = (
            db()
            .execute("SELECT * FROM jobs WHERE state='queued' ORDER BY rowid LIMIT 1")
            .fetchone()
        )
        if job:
            db().execute(
                "UPDATE jobs SET state='running',updated=CURRENT_TIMESTAMP WHERE id=?",
                (job["id"],),
            )
        db().commit()
        if job:
            try:
                process_job(job)
            except Exception as e:
                db().rollback()
                # HTTP errors may contain tokens in request URLs: never persist their text.
                message = (
                    str(e)
                    if isinstance(e, ValueError)
                    else "Remote request failed; check network access and credential configuration"
                )
                db().execute(
                    "UPDATE jobs SET state='failed',result=?,updated=CURRENT_TIMESTAMP WHERE id=? AND state!='cancelled'",
                    (message[:300], job["id"]),
                )
                db().commit()
        if once:
            return
        if not job:
            time.sleep(1)
