"""Versioned declarative import/preparation contracts. Never executes source code."""

import csv
import io
import json
import math
import re
import uuid
import zipfile
import openpyxl
from datetime import datetime
import pandas as pd

MAX_ROWS = 30000
RESERVED = "__id"


def path_get(value, path):
    for part in path.split(".") if path else []:
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def normalize(rows, identity=None):
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("Expected an array of record objects")
    if len(rows) > MAX_ROWS:
        raise ValueError(
            f"Interactive limit is {MAX_ROWS} records; choose an explicit extract"
        )
    out, seen = [], set()
    for row in rows:
        if any(not isinstance(k, str) or k.startswith("__") for k in row):
            raise ValueError("Field names beginning with __ are reserved")
        row = dict(row)
        rid = row.get(identity) if identity else uuid.uuid4().hex
        if rid is None or isinstance(rid, (dict, list, bool)) or str(rid) == "":
            raise ValueError("Identity must be a nonempty string or number")
        rid = str(rid)
        if rid in seen:
            raise ValueError(f"Duplicate identity: {rid}")
        seen.add(rid)
        row[RESERVED] = rid
        out.append(row)
    # reject non-finite JSON numbers, which cannot cross the browser contract
    json.dumps(out, allow_nan=False)
    return out


def parse_upload(blob, filename, options):
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext == "json":
        rows = path_get(json.loads(blob), options.get("records_path", ""))
    elif ext in ("csv", "tsv"):
        text = blob.decode(options.get("encoding", "utf-8-sig"))
        delimiter = options.get("delimiter") or ("\t" if ext == "tsv" else ",")
        if len(delimiter) != 1:
            raise ValueError("Delimiter must be one character")
        reader = csv.reader(io.StringIO(text), delimiter=delimiter, strict=True)
        headers = next(reader, [])
        if (
            not headers
            or len(set(headers)) != len(headers)
            or any(not h for h in headers)
        ):
            raise ValueError("Headers must be nonempty and unique")
        rows = []
        try:
            for cells in reader:
                if len(cells) != len(headers):
                    raise ValueError("Row width does not match headers")
                rows.append(dict(zip(headers, cells)))
        except csv.Error as e:
            raise ValueError(f"Malformed CSV: {e}") from e
    elif ext == "xlsx":
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                if (
                    sum(entry.file_size for entry in archive.infolist())
                    > 128 * 1024 * 1024
                ):
                    raise ValueError("Expanded workbook exceeds 128 MiB")
            workbook = openpyxl.load_workbook(
                io.BytesIO(blob), read_only=True, data_only=True
            )
            try:
                sheet = options.get("sheet", 0)
                selected = (
                    workbook.worksheets[sheet]
                    if isinstance(sheet, int)
                    else workbook[sheet]
                )
                headers = next(selected.iter_rows(values_only=True), ())
                if (
                    not headers
                    or any(h is None or h == "" for h in headers)
                    or len({str(h) for h in headers}) != len(headers)
                ):
                    raise ValueError("Workbook headers must be nonempty and unique")
            finally:
                workbook.close()
        except zipfile.BadZipFile as e:
            raise ValueError("Malformed XLSX workbook") from e
        # dtype=object avoids converting text identifiers such as 0012.
        frame = pd.read_excel(
            io.BytesIO(blob),
            sheet_name=options.get("sheet", 0),
            dtype=object,
            keep_default_na=False,
        )
        rows = frame.to_dict("records")
        rows = [
            {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in r.items()}
            for r in rows
        ]
    else:
        raise ValueError("Supported formats: CSV, TSV, JSON, XLSX")
    return normalize(rows, options.get("identity") or None)


def profile(rows):
    keys = list(dict.fromkeys(k for r in rows for k in r if k != RESERVED))
    fields = []
    for key in keys:
        vals = [r.get(key) for r in rows]
        present = [v for v in vals if v is not None and v != ""]
        kinds = {
            (
                "boolean"
                if isinstance(v, bool)
                else "number"
                if isinstance(v, (int, float))
                else "multivalue"
                if isinstance(v, list)
                else "object"
                if isinstance(v, dict)
                else "string"
            )
            for v in present
        }
        fields.append(
            {
                "id": key,
                "label": key,
                "type": next(iter(kinds)) if len(kinds) == 1 else "string",
                "role": "",
                "visible": True,
                "panel": "left",
                "missing": len(vals) - len(present),
                "unique": len({json.dumps(v, sort_keys=True) for v in present}),
                "samples": present[:4],
            }
        )
    return fields


def strict_number(value, step):
    if isinstance(value, bool):
        raise ValueError("Boolean is not numeric")
    text = str(value).strip()
    thousands, decimal = step.get("thousands", ""), step.get("decimal", ".")
    if thousands and thousands == decimal:
        raise ValueError("Decimal and thousands separators must differ")
    if thousands:
        # Reject malformed grouping rather than accepting arbitrary partial numbers.
        signless = text.lstrip("+-").split(decimal)[0]
        if thousands in signless and not re.fullmatch(
            r"\d{1,3}(?:" + re.escape(thousands) + r"\d{3})+", signless
        ):
            raise ValueError("Invalid thousands grouping")
        text = text.replace(thousands, "")
    text = text.replace(decimal, ".")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text):
        raise ValueError("Invalid complete number")
    result = float(text)
    if not math.isfinite(result):
        raise ValueError("Non-finite number")
    return result


def prepare(rows, steps):
    if not isinstance(steps, list) or len(steps) > 100:
        raise ValueError("Recipe must contain at most 100 operations")
    rows = json.loads(json.dumps(rows))
    errors = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("Each recipe operation must be an object")
        op, field = step.get("op"), step.get("field")
        if field == RESERVED or (isinstance(field, str) and field.startswith("__")):
            raise ValueError("Identity cannot be transformed")
        keys_available = {k for r in rows for k in r}
        if (
            op not in {"select", "deduplicate", "flatten"}
            and field not in keys_available
        ):
            raise ValueError(f"Unknown source field: {field}")
        if op == "deduplicate":
            keys = step.get("fields", [])
            if not keys:
                raise ValueError("Choose deduplication keys")
            seen, new = set(), []
            for r in rows:
                token = json.dumps([r.get(k) for k in keys], sort_keys=True)
                if token not in seen:
                    new.append(r)
                    seen.add(token)
            rows = new
            continue
        if op == "select":
            keys = step["fields"]
            rows = [
                {k: v for k, v in r.items() if k in keys or k == RESERVED} for r in rows
            ]
            continue
        if op not in {
            "trim",
            "blanks",
            "number",
            "boolean",
            "date",
            "year",
            "split",
            "join",
            "map",
            "rename",
            "flatten",
            "filter",
            "derive",
        }:
            raise ValueError(f"Unknown recipe operation: {op}")
        target = step.get("target", field)
        if not isinstance(target, str) or not target or target.startswith("__"):
            raise ValueError("Choose a valid target field")
        if (
            op in {"rename", "derive", "flatten"}
            and target != field
            and any(target in r for r in rows)
        ):
            raise ValueError("Target field already exists")
        new = []
        for r in rows:
            v = r.get(field)
            try:
                if op == "filter":
                    if v != step.get("equals"):
                        continue
                elif op == "rename":
                    if field in r:
                        r[target] = r.pop(field)
                elif op == "flatten":
                    r[target] = path_get(r, step["path"])
                elif op == "derive":
                    r[target] = (
                        step.get("then")
                        if v == step.get("equals")
                        else step.get("else")
                    )
                elif op == "trim":
                    r[target] = v.strip() if isinstance(v, str) else v
                elif op == "blanks":
                    r[target] = None if isinstance(v, str) and not v.strip() else v
                elif v is None or v == "":
                    pass
                elif op == "number":
                    r[target] = strict_number(v, step)
                elif op == "boolean":
                    if str(v).lower() not in ("true", "false", "1", "0"):
                        raise ValueError("Invalid boolean")
                    r[target] = str(v).lower() in ("true", "1")
                elif op == "date":
                    r[target] = datetime.strptime(str(v), step["format"]).isoformat()
                elif op == "year":
                    r[target] = datetime.strptime(str(v), step["format"]).year
                elif op == "split":
                    r[target] = str(v).split(step.get("delimiter", "|"))
                elif op == "join":
                    if not isinstance(v, list):
                        raise ValueError("Expected array")
                    r[target] = step.get("delimiter", "|").join(map(str, v))
                elif op == "map":
                    r[target] = step.get("values", {}).get(str(v), v)
            except (ValueError, TypeError, KeyError, IndexError) as e:
                errors.append(
                    {
                        "step": index,
                        "id": r[RESERVED],
                        "field": field,
                        "message": str(e),
                    }
                )
            new.append(r)
        rows = new
    return rows, errors


def validate_fields(fields, rows):
    keys = {f["id"] for f in profile(rows)}
    if (
        not isinstance(fields, list)
        or {f.get("id") for f in fields} != keys
        or len(fields) != len(keys)
    ):
        raise ValueError("Dictionary must describe each dataset field exactly once")
    allowed_roles = {
        "",
        "id",
        "title",
        "description",
        "date",
        "category",
        "measure",
        "latitude",
        "longitude",
        "link",
        "image",
        "x",
        "y",
    }
    clean = []
    for f in fields:
        if f.get("role", "") not in allowed_roles or f.get("type") not in {
            "string",
            "number",
            "boolean",
            "date",
            "multivalue",
            "object",
        }:
            raise ValueError("Invalid field role or type")
        if f.get("panel", "left") not in {"left", "right", "middle", "bottom", "none"}:
            raise ValueError("Invalid facet panel")
        if not isinstance(f.get("label"), str) or not f["label"].strip():
            raise ValueError("Field labels must be nonempty strings")
        for r in rows:
            value = r.get(f["id"])
            if value is None or value == "":
                continue
            kind = f["type"]
            if kind == "number" and (
                not isinstance(value, (int, float)) or isinstance(value, bool)
            ):
                raise ValueError(
                    "Convert the complete field with a number recipe before assigning numeric type"
                )
            if kind == "boolean" and not isinstance(value, bool):
                raise ValueError(
                    "Convert the complete field with a boolean recipe first"
                )
            if kind == "date":
                try:
                    datetime.fromisoformat(str(value))
                except ValueError:
                    raise ValueError(
                        "Convert dates with an explicit recipe format first"
                    )
        clean.append(
            {
                k: f[k]
                for k in (
                    "id",
                    "label",
                    "type",
                    "role",
                    "visible",
                    "panel",
                    "description",
                    "unit",
                    "delimiter",
                    "collapsed",
                )
                if k in f
            }
        )
    if len({f["label"] for f in clean}) != len(clean):
        raise ValueError("Field labels must be unique")
    return clean


def dashboard(value, fields):
    keys = {f["id"] for f in fields}
    allowed = {
        "name",
        "facets",
        "view",
        "title",
        "x",
        "y",
        "latitude",
        "longitude",
        "color",
        "size",
        "card",
        "collapsed",
    }
    result = {k: v for k, v in value.items() if k in allowed}
    for key in ("title", "x", "y", "latitude", "longitude", "color", "size"):
        if result.get(key) and result[key] not in keys:
            raise ValueError(f"Unknown field: {key}")
    if any(k not in keys for k in result.get("facets", [])):
        raise ValueError("Unknown facet")
    if result.get("view", "list") not in {"list", "scatter", "map"}:
        raise ValueError("Unsupported view")
    if "card" in result and (
        not isinstance(result["card"], list)
        or any(k not in keys for k in result["card"])
    ):
        raise ValueError("Cards use field tokens only")
    return result
