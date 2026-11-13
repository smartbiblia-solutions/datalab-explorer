# DataLab Explorer development

Use the existing checkout. Cloud tasks are isolated; create a Git worktree only when explicitly requested.

- Setup: `bash scripts/setup.sh` (Python 3.12, Node 22+).
- Web: `bash scripts/dev.sh`; worker: `bash scripts/worker.sh`.
- Container deployment: `docker compose up --build -d --wait`. Both services share the persistent `studio-data` volume; keep a single worker. Create accounts with `docker compose exec web python -m flask --app app add-user USERNAME`.
- Tests: `.venv/bin/python -m pytest -q`; `npm run typecheck`; `npm run build`; `npm run test:browser`.
- Browser tests run a dedicated temporary database on port 5101 and use system Chromium; never seed the real development database with test credentials.
- Keep original uploads and credentials private in ignored `instance/`. Never commit local databases or keys.
- Dataset versions and public releases are immutable. All project writes must pass central role checks and session CSRF validation. Public endpoints serve only approved frozen projections.
- User configurations are declarative JSON. No `eval`, `new Function`, or executable imported callbacks.
- Modify the readable Keshif source only, update `patches.json`, then build. The build verifies the complete patch chain against the recorded baseline. Never edit generated minified output by hand.
- Preserve exact IDs across chart/table/export and preserve explicit empty selections. Test public projection, stale-review rejection and revocation when changing publication.
- Keep `docs/implementation-status.md` honest about delivered versus deferred proposals.
