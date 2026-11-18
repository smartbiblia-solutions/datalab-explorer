import json

from conftest import csrf, upload

CSV = "Titre;Année;Équipe;Note interne\nA;2020;Eau;secret-1\nB;2021;Risques;secret-2\nC;2021;Eau;secret-3\n".encode("cp1252")


def test_private_pages_need_login(app):
    client = app.test_client()
    assert client.get("/admin/").status_code == 302
    assert client.get("/admin/donnees/x/lignes").status_code == 302
    assert client.get("/").status_code == 200


def test_post_without_csrf_is_refused(curator):
    assert curator.post("/admin/import", data={}).status_code == 400


def test_import_configure_publish_unpublish(app, curator):
    token = upload(curator, "équipes.csv", CSV)
    page = curator.get(f"/admin/import/{token}").get_data(as_text=True)
    assert "point-virgule" in page and "Note interne" in page
    r = curator.post(f"/admin/import/{token}", data={"name": "Équipes", "csrf_token": curator.token})
    view_id = r.headers["Location"].rsplit("/", 1)[-1]
    page = curator.get(f"/admin/vues/{view_id}").get_data(as_text=True)
    data = json.loads(page.split('id="view-data">')[1].split("</script>")[0])
    config = data["config"]
    for c in config["columns"]:
        c["include"] = c["column"] == "Équipe"
    config["display"].update(title="Titre", details=["Année"], sort="Année")
    r = curator.post(f"/admin/vues/{view_id}", json={"name": "Équipes", "config": config},
                     headers={"X-CSRF-Token": curator.token})
    assert r.status_code == 200, r.json
    r = curator.post(f"/admin/vues/{view_id}/publier",
                     data={"slug": "equipes", "title": "Nos équipes", "csrf_token": curator.token})
    assert r.status_code == 302
    anonymous = app.test_client()
    assert "Nos équipes" in anonymous.get("/").get_data(as_text=True)
    public = anonymous.get("/v/equipes/donnees").json
    assert "secret-1" not in json.dumps(public)
    assert set(public["rows"][0]) == {"_row", "Titre", "Année", "Équipe"}
    curator.post(f"/admin/vues/{view_id}/depublier", data={"csrf_token": curator.token})
    assert anonymous.get("/v/equipes").status_code == 404
    assert anonymous.get("/v/equipes/donnees").status_code == 404


def test_replace_keeps_view_and_publication_until_update(app, curator):
    token = upload(curator, "a.csv", b"name,group\nA,x\nB,y\n")
    view_id = curator.post(f"/admin/import/{token}", data={"name": "A", "csrf_token": curator.token}).headers["Location"].rsplit("/", 1)[-1]
    curator.post(f"/admin/vues/{view_id}/publier", data={"slug": "a", "title": "A", "csrf_token": curator.token})
    dataset_id = curator.get(f"/admin/vues/{view_id}").get_data(as_text=True).split("/admin/donnees/")[1].split('"')[0]
    token = upload(curator, "a2.csv", b"name,group,extra\nA,x,1\nB,y,2\nC,z,3\n", replace=dataset_id)
    curator.post(f"/admin/import/{token}", data={"csrf_token": curator.token})
    assert len(app.test_client().get("/v/a/donnees").json["rows"]) == 2
    curator.post(f"/admin/vues/{view_id}/publier", data={"slug": "a", "title": "A", "csrf_token": curator.token})
    assert len(app.test_client().get("/v/a/donnees").json["rows"]) == 3


def test_bad_file_shows_a_clear_error(curator):
    token = upload(curator, "bad.csv", b"a;b\n1;2;3\n")
    page = curator.get(f"/admin/import/{token}").get_data(as_text=True)
    assert "Ligne 2" in page


def test_language_switch(app):
    client = app.test_client()
    assert "Tableaux de bord publiés" in client.get("/").get_data(as_text=True)
    client.get("/lang/en")
    assert "Published dashboards" in client.get("/").get_data(as_text=True)
