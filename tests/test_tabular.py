import io
import json

import openpyxl
import pytest

from datalab.tabular import TableError, describe_columns, read_table
from datalab.views import default_config, public_rows, validate_config


def test_french_excel_csv():
    blob = "Titre;Année;Auteurs\nÉtude A;2024;Dupont J.;Martin A.\n".encode("cp1252")
    with pytest.raises(TableError) as e:
        read_table(blob, "x.csv")
    assert e.value.key == "error.csv_width" and e.value.params["line"] == 2
    blob = 'Titre;Année;Auteurs\nÉtude A;2024;"Dupont J.;Martin A."\nÉtude B;2023;Leroy P.\n'.encode("cp1252")
    t = read_table(blob, "x.csv")
    assert t["info"]["delimiter"] == ";" and t["info"]["encoding"] == "cp1252"
    assert t["columns"] == ["Titre", "Année", "Auteurs"]
    assert t["rows"][0] == {"_row": "1", "Titre": "Étude A", "Année": "2024", "Auteurs": "Dupont J.;Martin A."}


def test_codes_stay_text_and_types_are_guessed():
    blob = b"code,year,amount,tags,when\n0012,2020,1.5,a;b,2024-01-02\n0013,2021,2,c,2024-02-03\n0014,2022,3,a;c,2024-03-04\n"
    t = read_table(blob, "x.csv")
    kinds = {c["name"]: (c["type"], c["separator"]) for c in describe_columns(t["columns"], t["rows"])}
    assert kinds == {"code": ("text", ""), "year": ("year", ""), "amount": ("number", ""),
                     "tags": ("text", ";"), "when": ("date", "")}
    assert t["rows"][0]["code"] == "0012"


def test_headers_are_made_usable():
    t = read_table(b"a,,a\n1,2,3\n", "x.csv")
    assert t["columns"] == ["a", "colonne 2", "a (2)"]


def test_xlsx_and_json():
    wb = openpyxl.Workbook()
    wb.active.append(["id", "value", None])
    wb.active.append(["0012", 3.0, None])
    wb.create_sheet("Autre").append(["x"])
    blob = io.BytesIO()
    wb.save(blob)
    t = read_table(blob.getvalue(), "x.xlsx")
    assert t["info"]["sheets"] == ["Sheet", "Autre"]
    assert t["rows"][0]["id"] == "0012" and t["rows"][0]["value"] == 3
    j = read_table(json.dumps({"results": [{"a": 1, "tags": ["x", "y"]}, {"b": {"c": 1}}]}).encode(), "x.json")
    assert j["columns"] == ["a", "tags", "b"] and j["rows"][0]["tags"] == ["x", "y"]
    with pytest.raises(TableError):
        read_table(b"not a workbook", "x.xlsx")


def test_view_config_is_validated_and_publication_trimmed():
    t = read_table(b"title,kind,secret,year\nA,x,s1,2020\nB,y,s2,2021\nC,x,s3,2022\n", "x.csv")
    described = describe_columns(t["columns"], t["rows"])
    config = default_config(described, len(t["rows"]))
    shown = {c["column"] for c in config["columns"] if c["include"]}
    assert "kind" in shown and "year" in shown and config["display"]["title"] == "title"
    for c in config["columns"]:
        c["include"] = c["column"] == "kind"
    config["display"]["details"] = []
    config["display"]["sort"] = ""
    config["columns"].append({"column": "unknown", "include": True})
    clean = validate_config(config, t["columns"])
    assert [c["column"] for c in clean["columns"]] == t["columns"]
    published = public_rows(t["rows"], clean)
    assert published[0] == {"_row": "1", "title": "A", "kind": "x"}
    for c in config["columns"][:2]:
        c.update(include=True, label="Same")
    with pytest.raises(TableError):
        validate_config(config, t["columns"])
