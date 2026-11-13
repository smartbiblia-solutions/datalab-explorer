import pytest
from studio.jobs import validate_source, validate_url, run_worker
from studio.db import db, decode


@pytest.mark.parametrize(
    "url",
    [
        "http://api.openalex.org/works",
        "https://localhost/",
        "https://169.254.169.254/",
        "https://user:pass@api.openalex.org/",
        "https://unapproved.example/",
        "https://api.openalex.org:8443/",
    ],
)
def test_block_destinations(app, url):
    with app.app_context(), pytest.raises(ValueError):
        validate_url(url)


def test_worker_page_checkpoint_refresh(app, owner, dataset, monkeypatch):
    pid, old = dataset
    base = f"/api/projects/{pid}"
    pages = [
        {"results": [{"id": "0012", "n": 0}, {"id": "0013", "n": 2}]},
        {"results": [{"id": "0014", "n": 3}]},
    ]
    calls = []

    def fetch(url, params, headers):
        calls.append(params)
        return pages[len(calls) - 1]

    monkeypatch.setattr("studio.jobs.fetch_page", fetch)
    r = owner.post(
        base + "/jobs",
        {
            "url": "https://api.openalex.org/works",
            "pagination": "page",
            "page_size": 2,
            "identity": "id",
        },
    )
    assert r.status_code == 202, r.json
    with app.app_context():
        run_worker(True)
    jobs = owner.get(base + "/jobs").json
    assert jobs[0]["state"] == "succeeded" and jobs[0]["checkpoint"]["records"] == 3
    assert owner.get(base).json["project"]["active"] == old  # review before promotion
    assert calls == [{"page": 1, "per_page": 2}, {"page": 2, "per_page": 2}]


def test_limits_cancel_and_restart(app, owner, dataset, monkeypatch):
    pid, _ = dataset
    base = f"/api/projects/{pid}"
    monkeypatch.setattr(
        "studio.jobs.fetch_page", lambda *a: {"results": [{"id": "a"}, {"id": "b"}]}
    )
    j = owner.post(
        base + "/jobs", {"url": "https://api.openalex.org/works", "max_records": 1}
    ).json["id"]
    with app.app_context():
        run_worker(True)
    assert owner.get(base + "/jobs").json[0]["state"] == "failed"
    assert owner.post(base + f"/jobs/{j}/retry").json["restarted"]
    assert owner.post(base + f"/jobs/{j}/cancel").status_code == 200
    with app.app_context():
        run_worker(True)
    assert owner.get(base + "/jobs").json[0]["state"] == "cancelled"


def test_cursor_pages(app, owner, dataset, monkeypatch):
    pid, _ = dataset
    responses = iter(
        [
            {"results": [{"id": "a"}], "meta": {"next_cursor": "next"}},
            {"results": [{"id": "b"}], "meta": {"next_cursor": None}},
        ]
    )
    monkeypatch.setattr("studio.jobs.fetch_page", lambda *a: next(responses))
    owner.post(
        f"/api/projects/{pid}/jobs",
        {
            "url": "https://api.openalex.org/works",
            "pagination": "cursor",
            "identity": "id",
        },
    )
    with app.app_context():
        run_worker(True)
    assert owner.get(f"/api/projects/{pid}/jobs").json[0]["state"] == "succeeded"


def test_query_credentials_rejected(app):
    with app.app_context(), pytest.raises(ValueError):
        validate_url("https://api.openalex.org/works?api_key=do-not-store")


def test_redirect_policy_and_rate_retry(app, monkeypatch):
    from studio.jobs import fetch_page

    class Response:
        is_redirect = False
        headers = {"Retry-After": "0"}

        def __init__(self, code, payload=b'{"results":[]}'):
            self.status_code = code
            self.payload = payload

        def close(self):
            pass

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("HTTP error")

        def iter_content(self, _):
            yield self.payload

    calls = []
    responses = iter([Response(429), Response(200)])

    def get(*a, **k):
        calls.append(k)
        return next(responses)

    monkeypatch.setattr("studio.jobs.requests.get", get)
    with app.app_context():
        assert fetch_page("https://api.openalex.org/works", {}, {}) == {"results": []}
    assert len(calls) == 2 and all(c["allow_redirects"] is False for c in calls)
    redirect = Response(302)
    redirect.is_redirect = True
    redirect.headers = {"Location": "https://169.254.169.254/latest/"}
    monkeypatch.setattr("studio.jobs.requests.get", lambda *a, **k: redirect)
    with app.app_context(), pytest.raises(ValueError):
        fetch_page("https://api.openalex.org/works", {}, {})
