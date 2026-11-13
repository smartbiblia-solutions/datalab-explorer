# DataLab Explorer

A self-hosted data studio built with Flask, TypeScript and Keshif+. Import structured records, prepare them with repeatable recipes, describe variables, build dashboards, inspect exact selections, save research questions, collaborate and publish a reviewed public projection.

## Run locally

Requires Python 3.12+. Node 22+ is only needed to rebuild the frontend (`static/dist` is committed).

```sh
bash scripts/setup.sh
.venv/bin/python -m flask --app app add-user your-name
bash scripts/dev.sh
```

Open http://127.0.0.1:5000. The account command prompts for a password; there are no default accounts. API imports run in a background thread of the web process, so there is nothing else to start.

`instance/` holds the SQLite database, original uploads, API page checkpoints and the generated session key. Back it up before upgrades. `DATALAB_INSTANCE` moves it elsewhere; `SECRET_KEY` overrides the generated key. Use a TLS reverse proxy in production.

## Docker

```sh
docker compose up --build -d --wait
docker compose exec web python -m flask --app app add-user your-name
```

Data lives in the `studio-data` volume (`docker compose down` keeps it; `down --volumes` deletes everything). Run a single container: SQLite and the import thread assume one process.

Settings (shell or untracked `.env`):

| Variable | Default | Purpose |
|---|---|---|
| `DATALAB_PORT` | `5000` | Host port |
| `DATALAB_BIND_ADDRESS` | `127.0.0.1` | Use `0.0.0.0` only behind a TLS proxy |
| `DATALAB_API_HOSTS` | `api.openalex.org` | Comma-separated allowlist of HTTPS API hosts |
| `DATALAB_*` (any name) | — | Bearer tokens for API imports, referenced by name in a source; supply them through a private override, never in the repository |

## API imports

GET-only HTTPS requests to hosts in `DATALAB_API_HOSTS`. Redirects are re-checked against the allowlist and drop credentials across hosts; credentials in query strings are refused. Limits: 8 MiB per page, 100 pages, 30,000 records, 120 s per job. Hitting a limit fails the job instead of truncating. A refresh creates a new version but never replaces the active one automatically; compare versions in Sources, then activate.

## Workflow

1. Create a project and upload CSV/TSV, XLSX or JSON. CSV values stay strings until converted, so `0012` survives. Choose an identity column to compare refreshes.
2. Preview a declarative recipe against every row; errors block the new version. Applying creates a child version; undo reactivates the parent.
3. Edit labels, types, roles, panels and delimiters; choose a list, scatter or map dashboard, facets, encodings and record-card fields.
4. Keshif owns chart filtering; the table intersects the exact chart IDs with its own search. Save cohorts (empty ones stay empty) or questions with notes. Exports use the same IDs.
5. The owner grants editor/viewer roles to existing accounts.
6. Choose public fields, review the projected payload, then confirm. A release is frozen with new IDs and can be revoked.

## Verify

```sh
.venv/bin/python -m pytest -q
npm run typecheck
npm run build
npm run test:browser
```

Browser tests start their own temporary database on port 5101 and use `/usr/bin/chromium` (override with `CHROMIUM_PATH`).

## Keshif

`static/keshif/` is a copy of the [keshif-plus-custom](https://github.com/smartbiblia-solutions/keshif-plus-custom) fork, pinned to the commit in `static/keshif/VERSION`. Fix the renderer in the fork, then update the copy:

```sh
bash scripts/update-keshif.sh <commit-or-tag>
```

Keshif+ is © Keshif LLC; see `static/keshif/LICENSE` and `static/keshif/NOTICE.md` for its licence and bundled third-party libraries (including Font Awesome 6 Free).

## Licence

DataLab Explorer is licensed under the [GNU AGPL v3](LICENSE).
