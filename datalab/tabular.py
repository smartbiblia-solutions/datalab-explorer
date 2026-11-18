"""Read CSV, TSV, XLSX and JSON files into rows, and describe their columns."""

import csv
import io
import json
import re
import zipfile
from datetime import date, datetime

import openpyxl

MAX_ROWS = 50_000
ROW_ID = "_row"
SEPARATORS = {";": "point-virgule", ",": "virgule", "\t": "tabulation", "|": "barre verticale"}
ENCODINGS = ["utf-8-sig", "cp1252"]


class TableError(ValueError):
    """An error shown to the curator. `key` is a translation key, `params` fill it."""

    def __init__(self, key, **params):
        super().__init__(key)
        self.key, self.params = key, params


def read_table(blob, filename, options=None):
    """Return {"columns": [...], "rows": [...], "info": {...}} for an uploaded file."""
    options = options or {}
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext in ("csv", "tsv", "txt"):
        columns, records, info = _read_csv(blob, options, tsv=ext == "tsv")
    elif ext == "xlsx":
        columns, records, info = _read_xlsx(blob, options)
    elif ext == "json":
        columns, records, info = _read_json(blob)
    else:
        raise TableError("error.format")
    if not records:
        raise TableError("error.empty")
    if len(records) > MAX_ROWS:
        raise TableError("error.too_many_rows", limit=MAX_ROWS, found=len(records))
    columns, renamed = _clean_headers(columns)
    rows = []
    for i, values in enumerate(records):
        row = {ROW_ID: str(i + 1)}
        row.update(zip(columns, values))
        rows.append(row)
    info["renamed"] = renamed
    return {"columns": columns, "rows": rows, "info": info}


def _decode(blob, wanted):
    for encoding in [wanted] if wanted else ENCODINGS:
        try:
            return blob.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            continue
    raise TableError("error.encoding")


def _guess_delimiter(text, tsv):
    if tsv:
        return "\t"
    sample = text[:65536]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
    except csv.Error:
        first = sample.splitlines()[0] if sample else ""
        return max(SEPARATORS, key=first.count)


def _read_csv(blob, options, tsv=False):
    text, encoding = _decode(blob, options.get("encoding"))
    delimiter = options.get("delimiter") or _guess_delimiter(text, tsv)
    if delimiter not in SEPARATORS:
        raise TableError("error.delimiter")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        lines = [line for line in reader]
    except csv.Error as e:
        raise TableError("error.csv", detail=str(e)) from e
    lines = [line for line in lines if any(cell.strip() for cell in line)]
    if not lines:
        raise TableError("error.empty")
    header, body = lines[0], lines[1:]
    for number, line in enumerate(body, start=2):
        if len(line) != len(header):
            raise TableError(
                "error.csv_width", line=number, expected=len(header), found=len(line)
            )
    info = {"format": "CSV", "delimiter": delimiter, "encoding": encoding}
    return header, [[cell.strip() for cell in line] for line in body], info


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        return value.strip()
    return value


def _read_xlsx(blob, options):
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            if sum(e.file_size for e in archive.infolist()) > 200 * 1024 * 1024:
                raise TableError("error.xlsx_size")
        workbook = openpyxl.load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
    except (zipfile.BadZipFile, OSError, KeyError) as e:
        raise TableError("error.xlsx") from e
    try:
        sheets = workbook.sheetnames
        sheet = options.get("sheet") or sheets[0]
        if sheet not in sheets:
            raise TableError("error.sheet", sheet=sheet)
        lines = [
            [_cell(v) for v in values]
            for values in workbook[sheet].iter_rows(values_only=True)
            if any(v not in (None, "") for v in values)
        ]
    finally:
        workbook.close()
    if not lines:
        raise TableError("error.empty")
    width = max(len(line) for line in lines)
    lines = [line + [""] * (width - len(line)) for line in lines]
    header = [str(h) for h in lines[0]]
    info = {"format": "XLSX", "sheet": sheet, "sheets": sheets}
    return header, lines[1:], info


def _read_json(blob):
    try:
        data = json.loads(blob.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise TableError("error.json") from e
    if isinstance(data, dict):  # {"results": [...]} or {"data": [...]}: take the first list of objects
        data = next((v for v in data.values() if isinstance(v, list)), None)
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise TableError("error.json_records")
    header = list(dict.fromkeys(k for r in data for k in r))

    def value(v):
        if v is None:
            return ""
        if isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v):
            return [x for x in v if x not in (None, "")]
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return v.strip() if isinstance(v, str) else v

    return header, [[value(r.get(k)) for k in header] for r in data], {"format": "JSON"}


def _clean_headers(columns):
    """Empty headers get a name, duplicates a suffix, so every column can be addressed."""
    seen, result, renamed = set(), [], []
    for i, name in enumerate(columns, start=1):
        clean = str(name).strip() or f"colonne {i}"
        if clean == ROW_ID:
            clean = f"{ROW_ID} (fichier)"
        base, n = clean, 2
        while clean in seen:
            clean, n = f"{base} ({n})", n + 1
        if clean != str(name):
            renamed.append([str(name), clean])
        seen.add(clean)
        result.append(clean)
    return result, renamed


NUMBER = re.compile(r"^-?\d+(?:[.,]\d+)?$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+)?$")
FR_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def _number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str) and NUMBER.match(v) and not (len(v) > 1 and v.startswith("0") and v[1:2] not in (".", ",")):
        return float(v.replace(",", "."))
    return None


def describe_columns(columns, rows):
    """Guess a type and a multi-value separator for each column, from all its values."""
    described = []
    for name in columns:
        values = [r.get(name) for r in rows]
        present = [v for v in values if v not in ("", None, [])]
        kind, separator = "text", ""
        if any(isinstance(v, list) for v in present):
            kind = "list"
        elif present:
            numbers = [_number(v) for v in present]
            if all(n is not None for n in numbers):
                integers = all(float(n).is_integer() for n in numbers)
                kind = "year" if integers and all(1000 <= n <= 2100 for n in numbers) else "number"
            elif all(isinstance(v, str) and (ISO_DATE.match(v) or FR_DATE.match(v)) for v in present):
                kind = "date"
            else:
                texts = [v for v in present if isinstance(v, str)]
                for sep in (";", "|"):
                    if texts and sum(sep in v for v in texts) >= max(2, len(texts) // 10):
                        separator = sep
                        break
        distinct = len({json.dumps(v, ensure_ascii=False, sort_keys=True) for v in present})
        described.append(
            {
                "name": name,
                "type": kind,
                "separator": separator,
                "missing": len(values) - len(present),
                "distinct": distinct,
                "samples": [str(v)[:60] for v in present[:3]],
            }
        )
    return described
