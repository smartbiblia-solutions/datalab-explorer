"""View configurations: plain JSON describing a Keshif dashboard. No code is ever stored."""

import re

from .tabular import ROW_ID, TableError

PANELS = ("left", "middle", "right", "bottom")
TYPES = ("text", "number", "year", "date")
LAYOUTS = ("list", "grid")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def default_config(described, row_count):
    """A first dashboard: categorical columns as facets, a year or date at the bottom."""
    columns, facets, timeline = [], 0, False
    for c in described:
        kind = "text" if c["type"] == "list" else c["type"]
        entry = {
            "column": c["name"],
            "label": c["name"],
            "type": kind,
            "separator": c["separator"],
            "panel": "left" if facets < 4 else "right",
            "include": False,
            "collapsed": False,
        }
        categorical = kind == "text" and (
            c["separator"] or c["type"] == "list" or 2 <= c["distinct"] <= max(60, row_count // 20)
        )
        if categorical and facets < 8 and c["distinct"] < row_count:
            entry["include"] = True
            facets += 1
        elif kind in ("year", "date") and not timeline:
            entry.update(include=True, panel="bottom")
            timeline = True
        columns.append(entry)
    texts = [c for c in described if c["type"] == "text" and not c["separator"]]
    title = max(texts, key=lambda c: c["distinct"])["name"] if texts else described[0]["name"]
    sort = next((c["name"] for c in described if c["type"] in ("year", "date", "number")), "")
    return {
        "columns": columns,
        "display": {
            "layout": "list",
            "title": title,
            "link": "",
            "details": [c["column"] for c in columns if c["include"]][:3],
            "sort": sort,
            "sort_desc": True,
        },
    }


def validate_config(config, columns):
    """Return a clean copy of a view configuration, or raise TableError."""
    known = set(columns)
    if not isinstance(config, dict) or not isinstance(config.get("columns"), list):
        raise TableError("error.view")
    clean, seen, labels = [], set(), set()
    for c in config["columns"]:
        if not isinstance(c, dict) or c.get("column") not in known or c["column"] in seen:
            continue  # columns removed by a re-import are dropped silently
        seen.add(c["column"])
        label = str(c.get("label") or c["column"]).strip()[:120]
        entry = {
            "column": c["column"],
            "label": label,
            "type": c.get("type") if c.get("type") in TYPES else "text",
            "separator": str(c.get("separator") or "")[:3],
            "panel": c.get("panel") if c.get("panel") in PANELS else "left",
            "include": c.get("include") is True,
            "collapsed": c.get("collapsed") is True,
        }
        if entry["include"]:
            if label in labels:
                raise TableError("error.duplicate_label", label=label)
            labels.add(label)
        clean.append(entry)
    for name in columns:  # columns added by a re-import appear, not shown by default
        if name not in seen:
            clean.append({"column": name, "label": name, "type": "text", "separator": "",
                          "panel": "left", "include": False, "collapsed": False})
    d = config.get("display") if isinstance(config.get("display"), dict) else {}
    pick = lambda v: v if v in known else ""
    sort = pick(d.get("sort"))
    if sort and next(c["type"] for c in clean if c["column"] == sort) == "text":
        sort = ""
    display = {
        "layout": d.get("layout") if d.get("layout") in LAYOUTS else "list",
        "title": pick(d.get("title")) or columns[0],
        "link": pick(d.get("link")),
        "details": [x for x in d.get("details", []) if x in known][:6] if isinstance(d.get("details"), list) else [],
        "sort": sort,
        "sort_desc": d.get("sort_desc") is not False,
    }
    return {"columns": clean, "display": display}


def used_columns(config):
    d = config["display"]
    used = [c["column"] for c in config["columns"] if c["include"]]
    used += [d["title"], d["link"], d["sort"], *d["details"]]
    return [c for c in dict.fromkeys(used) if c]


def public_rows(rows, config):
    """The published copy keeps only the columns the view shows."""
    keep = used_columns(config)
    return [{ROW_ID: r[ROW_ID], **{k: r.get(k, "") for k in keep}} for r in rows]


def check_slug(slug):
    slug = (slug or "").strip().lower()
    if not SLUG.match(slug) or len(slug) > 80:
        raise TableError("error.slug")
    return slug
