import pytest
from studio import create_app
from studio.db import db
from werkzeug.security import generate_password_hash


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "SECRET_KEY": "test-key",
            "API_HOSTS": ["api.openalex.org", "api.example.org"],
        }
    )
    with app.app_context():
        for name in ("owner", "editor", "viewer", "outsider"):
            db().execute(
                "INSERT INTO users(username,password) VALUES (?,?)",
                (name, generate_password_hash("test-password")),
            )
        db().commit()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class Session:
    def __init__(self, client, username="owner"):
        self.client = client
        self.csrf = client.get("/api/session").json["csrf"]
        result = self.post(
            "/api/login", {"username": username, "password": "test-password"}
        )
        self.csrf = result.json["csrf"]

    def post(self, path, body=None, **kwargs):
        if "data" in kwargs:
            return self.client.post(path, headers={"X-CSRF-Token": self.csrf}, **kwargs)
        return self.client.post(
            path, json=body or {}, headers={"X-CSRF-Token": self.csrf}, **kwargs
        )

    def get(self, path):
        return self.client.get(path)


@pytest.fixture
def owner(client):
    return Session(client)


@pytest.fixture
def dataset(owner):
    import io

    pid = owner.post("/api/projects", {"name": "Example"}).json["id"]
    r = owner.post(
        f"/api/projects/{pid}/imports",
        data={
            "file": (
                io.BytesIO(
                    b"id,title,value,secret\n0012,Alpha,0,private-A\n0013,Beta,2,private-B\n"
                ),
                "data.csv",
            ),
            "options": '{"identity":"id"}',
        },
    )
    assert r.status_code == 201, r.json
    return pid, r.json["id"]
