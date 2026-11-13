import re

import pytest
from werkzeug.security import generate_password_hash

from datalab import create_app
from datalab.db import db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATALAB_INSTANCE", str(tmp_path))
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    with app.app_context():
        db().execute("INSERT INTO users(username, password) VALUES ('curator', ?)",
                     (generate_password_hash("curator-password"),))
        db().commit()
    return app


def csrf(client, path="/connexion"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


@pytest.fixture
def curator(app):
    client = app.test_client()
    token = csrf(client)
    r = client.post("/connexion", data={"username": "curator", "password": "curator-password", "csrf_token": token})
    assert r.status_code == 302
    client.token = token
    return client


def upload(client, name, content, **extra):
    import io

    r = client.post("/admin/import", data={"file": (io.BytesIO(content), name), "csrf_token": client.token, **extra},
                    content_type="multipart/form-data")
    assert r.status_code == 302, r.get_data(as_text=True)
    return r.headers["Location"].rsplit("/", 1)[-1]
