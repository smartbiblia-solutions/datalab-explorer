import io
import json
import pytest
from conftest import Session
from studio.data import parse_upload, normalize, profile, prepare
from studio.db import db


def test_identity_and_types():
    rows = parse_upload(b"id,n,b\n0012,0,false\n", "x.csv", {"identity": "id"})
    assert rows[0]["id"] == "0012" and rows[0]["__id"] == "0012"
    n = normalize([{"id": "000", "zero": 0, "flag": False, "nullable": None}], "id")
    fields = {f["id"]: f for f in profile(n)}
    assert fields["zero"]["type"] == "number" and fields["flag"]["type"] == "boolean"
    assert fields["zero"]["missing"] == 0 and fields["flag"]["missing"] == 0
    with pytest.raises(ValueError):
        normalize([{"id": "a"}, {"id": "a"}], "id")


@pytest.mark.parametrize("blob", [b"a,a\n1,2", b"a,b\n1", b'a\n"unterminated', b""])
def test_bad_csv(blob):
    with pytest.raises(ValueError):
        parse_upload(blob, "bad.csv", {})


def test_json_union_and_xlsx():
    rows = parse_upload(
        b'{"results":[{"a":0},{"b":false}]}', "data.json", {"records_path": "results"}
    )
    assert {f["id"] for f in profile(rows)} == {"a", "b"}
    import openpyxl

    workbook = openpyxl.Workbook()
    workbook.active.append(["id", "amount"])
    workbook.active.append(["0012", 0])
    blob = io.BytesIO()
    workbook.save(blob)
    assert (
        parse_upload(blob.getvalue(), "x.xlsx", {"identity": "id"})[0]["id"] == "0012"
    )


def test_recipe_strict_and_replay():
    rows = normalize(
        [
            {
                "id": "0012",
                "name": " A ",
                "amount": "1 234,5",
                "bad": "12x",
                "date": "31/12/2025",
                "tags": "a|b",
            }
        ],
        "id",
    )
    steps = [
        {"op": "trim", "field": "name"},
        {"op": "number", "field": "amount", "decimal": ",", "thousands": " "},
        {"op": "date", "field": "date", "format": "%d/%m/%Y"},
        {"op": "split", "field": "tags"},
    ]
    a, errors = prepare(rows, steps)
    assert not errors
    assert (
        a[0]["amount"] == 1234.5 and a[0]["name"] == "A" and a[0]["tags"] == ["a", "b"]
    )
    assert prepare(rows, steps)[0] == a and rows[0]["name"] == " A "
    assert prepare(rows, [{"op": "number", "field": "bad"}])[1][0]["id"] == "0012"
    with pytest.raises(ValueError):
        prepare(rows, [{"op": "rename", "field": "name", "target": "__id"}])


def test_core_workflow(owner, dataset):
    pid, vid = dataset
    base = f"/api/projects/{pid}"
    version = owner.get(base + "/versions/" + vid).json
    assert version["rows"][0]["id"] == "0012"
    steps = [{"op": "number", "field": "value"}]
    preview = owner.post(
        base + "/prepare", {"version": vid, "steps": steps, "preview": True}
    )
    assert preview.json["rows"][0]["value"] == 0
    new = owner.post(base + "/prepare", {"version": vid, "steps": steps}).json["id"]
    assert owner.get(base + "/versions/" + vid).json == version
    assert owner.get(base + "/versions/" + new).json["parent"] == vid
    cohort = owner.post(
        base + "/objects",
        {"kind": "cohort", "payload": {"version": new, "ids": [], "name": "Empty"}},
    )
    assert cohort.status_code == 201
    assert (
        owner.post(base + "/selection-export", {"version": new, "ids": []}).json == []
    )
    manifest = owner.get(base + "/export").json
    assert "raw" not in json.dumps(manifest)
    imported = owner.post("/api/project-import", manifest)
    assert imported.status_code == 201, imported.json
    copy = owner.get("/api/projects/" + imported.json["id"]).json
    assert len(copy["versions"]) == 2 and copy["objects"][0]["payload"]["ids"] == []
    diff = owner.get(base + f"/diff?a={vid}&b={new}").json
    assert diff["changed"] == ["0012", "0013"] and not diff["added"]


def test_roles_and_downgrades(app, owner, dataset):
    pid, vid = dataset
    base = f"/api/projects/{pid}"
    for username, role in [("editor", "editor"), ("viewer", "viewer")]:
        assert (
            owner.post(
                base + "/members", {"username": username, "role": role}
            ).status_code
            == 200
        )
    editor = Session(app.test_client(), "editor")
    viewer = Session(app.test_client(), "viewer")
    outsider = Session(app.test_client(), "outsider")
    assert viewer.get(base + "/versions/" + vid).status_code == 200
    assert viewer.post(base + "/prepare", {"steps": []}).status_code == 403
    assert (
        viewer.post(
            base + "/objects",
            {"kind": "cohort", "payload": {"version": vid, "ids": []}},
        ).status_code
        == 403
    )
    assert editor.post(base + "/prepare", {"steps": []}).status_code == 201
    assert (
        editor.post(base + "/publication-preview", {"fields": ["title"]}).status_code
        == 403
    )
    assert outsider.get(base).status_code == 404
    assert (
        owner.post(
            base + "/members", {"username": "owner", "role": "remove"}
        ).status_code
        == 400
    )
    owner.post(base + "/members", {"username": "editor", "role": "viewer"})
    assert editor.post(base + "/prepare", {"steps": []}).status_code == 403
    owner.post(base + "/members", {"username": "editor", "role": "remove"})
    assert editor.get(base).status_code == 404


def test_publication_projection_stale_and_revoke(app, owner, dataset):
    pid, vid = dataset
    base = f"/api/projects/{pid}"
    b = {
        "version": vid,
        "title": "Public dataset",
        "fields": ["title", "value"],
        "dashboard": {"view": "list", "source": "private", "onReady": "evil()"},
    }
    review = owner.post(base + "/publication-preview", b).json
    assert set(review["preview"]) == {
        "schema",
        "title",
        "rows",
        "fields",
        "dashboard",
        "data_date",
    }
    text = json.dumps(review["preview"])
    for forbidden in (
        "private-A",
        "private-B",
        "0012",
        "secret",
        "source",
        "onReady",
        "raw",
        "samples-private",
    ):
        assert forbidden not in text
    assert (
        owner.post(
            base + "/releases",
            {**b, "fields": ["title"], "digest": review["digest"], "confirmed": True},
        ).status_code
        == 409
    )
    result = owner.post(
        base + "/releases", {**b, "digest": review["digest"], "confirmed": True}
    )
    assert result.status_code == 201
    rid = result.json["id"]
    anonymous = app.test_client()
    original = anonymous.get("/public/" + rid + "/data").json
    owner.post(base + "/prepare", {"steps": [{"op": "trim", "field": "title"}]})
    assert anonymous.get("/public/" + rid + "/data").json == original
    assert anonymous.get(base).status_code == 401
    assert anonymous.get(base + "/export").status_code == 401
    owner.post(base + "/releases/" + rid + "/revoke")
    for suffix in ("", "/data", "/export"):
        assert anonymous.get("/public/" + rid + suffix).status_code == 404


def test_csrf_and_malformed(owner, dataset, client):
    pid, vid = dataset
    base = f"/api/projects/{pid}"
    assert client.post(base + "/prepare", json={"steps": []}).status_code == 403
    for body in (
        {"steps": None},
        {"steps": [{"op": "eval", "field": "title"}]},
        {"steps": [{"op": "rename", "field": "title", "target": "secret"}]},
    ):
        assert owner.post(base + "/prepare", body).status_code == 400
    assert (
        owner.post(
            base + "/objects",
            {"kind": "dictionary", "payload": {"version": vid, "fields": []}},
        ).status_code
        == 400
    )
    assert owner.post("/api/project-import", {"schema": 999}).status_code == 400


def test_dictionary_requires_full_conversion(owner, dataset):
    pid, vid = dataset
    base = f"/api/projects/{pid}"
    fields = owner.get(base + "/versions/" + vid).json["fields"]
    next(f for f in fields if f["id"] == "value")["type"] = "number"
    assert (
        owner.post(
            base + "/objects",
            {"kind": "dictionary", "payload": {"version": vid, "fields": fields}},
        ).status_code
        == 400
    )
    assert owner.post(base + "/prepare", {"steps": [None]}).status_code == 400
    assert (
        owner.post(
            base + "/prepare", {"steps": [{"op": "trim", "field": "absent"}]}
        ).status_code
        == 400
    )


def test_malformed_xlsx_and_duplicate_headers():
    with pytest.raises(ValueError):
        parse_upload(b"not-a-workbook", "x.xlsx", {})
    import openpyxl

    workbook = openpyxl.Workbook()
    workbook.active.append(["a", "a"])
    workbook.active.append([1, 2])
    blob = io.BytesIO()
    workbook.save(blob)
    with pytest.raises(ValueError):
        parse_upload(blob.getvalue(), "x.xlsx", {})
