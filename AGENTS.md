# DataLab Explorer development

Use the existing checkout. Cloud tasks are isolated; create a Git worktree only when explicitly requested.

- Setup: `bash scripts/setup.sh` (Python 3.12+, Node 22+). Web and API-import thread: `bash scripts/dev.sh`.
- Container deployment: `docker compose up --build -d --wait`, one container with the `studio-data` volume. Create accounts with `docker compose exec web python -m flask --app app add-user USERNAME`.
- Tests: `.venv/bin/python -m pytest -q`; `npm run typecheck`; `npm run build`; `npm run test:browser`.
- Browser tests run a dedicated temporary database on port 5101; never seed the real development database with test credentials.
- `static/dist` (built from `frontend/`) and `static/keshif` are committed. Rebuild `static/dist` after frontend changes.
- Keshif: change it in the keshif-plus-custom fork (see its README rules: opt-in options, Portic tests), then `bash scripts/update-keshif.sh <ref>`. Never edit `static/keshif` by hand.
- Keep original uploads and credentials private in ignored `instance/`. Never commit local databases or keys.
- Dataset versions and public releases are immutable. All project writes must pass central role checks and session CSRF validation. Public endpoints serve only approved frozen projections.
- User configurations are declarative JSON. No `eval`, `new Function`, or executable imported callbacks.
- Preserve exact IDs across chart/table/export and preserve explicit empty selections. Test public projection, stale-review rejection and revocation when changing publication.
- Keep `docs/implementation-status.md` honest about delivered versus deferred proposals.
