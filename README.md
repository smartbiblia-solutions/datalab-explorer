# DataLab Explorer

A self-hosted data studio built with Flask, TypeScript and a retained Keshif+ renderer. Import structured records, prepare repeatable recipes, map variables, build dashboards, inspect exact selections, save research questions, collaborate and publish an explicitly reviewed projection.

## Start

Python **3.12**, Node **22+**, npm and Chromium are required. No AI service, Docker or external database is required. Use the existing checkout; cloud tasks are already isolated and do not need a Git worktree.

```sh
bash scripts/setup.sh
.venv/bin/python -m flask --app app add-user your-name
bash scripts/dev.sh
# In another terminal, for API imports:
bash scripts/worker.sh
```

The account CLI prompts for a password. There are no default development credentials. Web listens on port 5000; `GET /health` reports schema/build readiness. Start the processes again after restoring a cloud snapshot. Run from the repository root. `instance/` contains private SQLite metadata, original uploads, API page checkpoints and the persistent session key; back it up before upgrades. `DATALAB_INSTANCE` can put that directory elsewhere. Set `SECRET_KEY` through deployment secret settings if centrally managing sessions; never commit its value. Configure secure cookies and a TLS reverse proxy for production.

The worker accepts **GET-only HTTPS** APIs. `api.openalex.org` is enabled by default. Add trusted public API hosts to the comma-separated server variable `DATALAB_API_HOSTS`, and to the hosting platform's outbound policy. This is an administrator allowlist, not an end-user bypass. Every redirect is checked and cross-host credentials are removed. Bearer credentials use a server-side `DATALAB_*` environment-variable reference; values never belong in project manifests. Do not put credentials in query strings. Requests are bounded by page, record, response-size and time limits; see [architecture](docs/architecture.md).

## Workflow

1. Create a project and upload CSV/TSV, XLSX or JSON. CSV values remain strings until explicitly converted, so `0012` survives. Choose a natural identity to compare refreshes; otherwise IDs are immutable-version-local.
2. Preview a declarative preparation recipe against every row. Invalid conversions report affected IDs and block creation of a version. Applying creates a child version; undo activates its parent without deleting history.
3. Edit labels, types, semantic roles, facet panels and multivalue delimiters. Choose a list, scatter or map dashboard, facets, encodings and safe record-card fields. Numeric scatter fields must first be converted to numbers. Dates require an explicit preparation format.
4. Keshif owns chart filtering. The record table intersects exact chart IDs with its independent search and exact-value predicate. Save an exact cohort or a question with notes and dashboard/table state. Empty cohorts remain empty. JSON exports use that same intersection.
5. The owner grants editor/viewer membership to existing accounts. Viewer requests cannot mutate projects, even by direct HTTP calls.
6. Select a public field allowlist, review the complete projected payload, then explicitly confirm its digest. Each public release has independent data/metadata and replacement IDs. It never serves the private project manifest. Revoke a release to return 404 for its reader, data and export endpoints.

Several dashboards and recipe templates can be saved per project. Portable project manifests include versioned data, mappings, recipes, dashboards and questions; exclude raw-file locations, source URLs and credential configuration. Imports validate IDs and references. Refreshes from the worker produce reviewable versions without automatically replacing an existing active dataset. Compare versions in Sources before activating.

## Verify

```sh
.venv/bin/python -m pytest -q
npm run typecheck
npm run build
npm run test:browser
```

Browser tests use system Chromium (`/usr/bin/chromium`) and their own temporary database/account; they do not require development credentials. On other machines set `CHROMIUM_PATH`. Playwright's managed Chromium is an alternative after installing it from its official distribution. Build outputs are committed so the app can start from a checkout; `npm ci && npm run build` reproduces them using locked tools. Every build writes a checksum manifest.

[Reconstruction scope and acceptance status](docs/implementation-status.md) distinguishes delivered behavior, tested contracts and proposed extensions. [Validation](docs/validation.md) records actual results and remaining limitations. Original uploaded documents are retained in `docs/`; their historical approval instructions are reference material, not current task authorization.

## Keshif provenance

The canonical readable renderer and its vendor modules live in `vendor/keshif/`, independently of the removed examples. [Patch ledger](vendor/keshif/PATCHES.md), baseline checksums and build manifest document provenance. The inherited distribution cannot be proven identical to current upstream. Upstream's BSD-style LICENSE and AGPL package-metadata conflict is explicitly recorded in [third-party notices](vendor/THIRD-PARTY-NOTICES.md). This reconstruction does not assert that conflict is legally resolved. Font Awesome Pro faces are not distributed: the build uses the separately licensed Font Awesome Free package.
