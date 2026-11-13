# Validation record

Reconstructed and checked on 13 November 2026 in the managed Linux cloud environment (Python 3.12, Node 24, system Chromium).

## Reproducibility

- A fresh repository-local `.venv` was created from the pinned requirements.
- `bash scripts/setup.sh` completed: locked Python dependencies, `npm ci`, TypeScript check, frontend/vendor build, dependency consistency check.
- Each frontend build reverses the Keshif patch ledger and checks the original SHA-256 baseline before generating matching minified JS/source maps and a complete runtime checksum manifest.
- `npm run typecheck` and `git diff --check` passed.
- After removing all legacy application files, the standalone setup completed again, followed by **25 passing Python tests** and **4 passing Chromium tests**. Remaining empty upload directories were then removed; no `archives/` directory remains. The app/build have no runtime reference to that directory.

## Server tests

`python -m pytest -q`: **25 passed**, no skipped tests. Covers exact string identities, zero/false/null, malformed CSV/XLSX and duplicate headers, JSON field union, sheet import, strict preparation/replay, immutable versions, empty cohorts/exports, portable manifest import/export, roles and direct HTTP mutations after downgrade/removal, original owner protection, CSRF, malformed requests, genuine version-1 migration fixture, reviewed publication projection, stale review rejection, anonymous private access denial, frozen releases and all revoked endpoint 404s. Worker fixtures cover page/cursor modes, progress, limits, cancellation, explicit restart, transient retries, redirect destination policy and query-credential rejection.

## Browser tests

`npm run test:browser`: **4 passed**, no skipped tests. The Playwright suite uses a temporary isolated database, a test-only seeded account and actual `/usr/bin/chromium`. It exercises:

1. Import → prepare → native categorical filtering → synchronized table → empty pinned cohort → FR/EN → reviewed publication → anonymous native filter → language-preserved membership → revoke.
2. Native Keshif zero/false inference and clustering with absent geometry plus all 1,201 coincident members.
3. Six list/scatter/map remounts, hidden/reopened tabs and 390/768px widths, with uncaught page errors treated as failures.
4. No-coordinate dataset: valid empty map and all records still available in the table.

The public reader waits for the adapter's completed mount, verifies that the inactive overlay is hidden and checks exact table membership after language changes. Tooltip instances and transitions are cleaned before remounting. Selection restoration runs after Keshif's native finalization (its onReady callback precedes that finalization).

Screenshots are generated in `test-results/`; selected evidence is retained in `docs/screenshots/`.

## Live API check

A bounded, unauthenticated request to OpenAlex returned HTTP 200. A separate temporary-database run of the real worker imported and persisted one work from `https://api.openalex.org/works?per_page=1&select=id,title,publication_year` with state `succeeded`, one page and one record. This does not guarantee future API availability, other endpoints, or credential access. Deterministic tests do not depend on OpenAlex.

## Limits

No 30k-record p95 or 100k stress benchmark is certified. Interactive imports explicitly cap at 30,000 rows rather than silently sampling. Full keyboard/screen-reader certification, rich timeseries, generic joins, arbitrary graph/embedding generation, advanced decision models and full native Keshif translation are not claimed. Common studio/table/native facet labels are bilingual; some advanced native dialogs and operator technical names remain English. The exact lost implementation and database format were unavailable; the supplied v1 migration is for this documented reconstructed schema.

Upstream license metadata remains inconsistent; see third-party notices. The inherited duplicate `recordGeo` switch case is a documented, harmless esbuild warning, not a failed build.

## Container deployment

The multi-stage Docker image builds the locked Python environment and recompiles the frontend with its TypeScript and vendor integrity checks. Docker Compose v2 configuration validation passed. Web and worker containers both became healthy with a read-only root filesystem, UID 10001 and a shared named data volume. All 32 frontend artifact checksums matched inside the runtime image.

A disposable Compose project passed account creation through the container CLI, login, CSV import with a leading-zero identity, and a real OpenAlex job processed by the separate worker. Containers and their network were removed and recreated while retaining the volume: projects, rows, completed job history and the authenticated session survived. Actual Chromium rendered the native Keshif dashboard served by Docker. The disposable test containers and volume were then removed. Cloud-specific CA certificates were mounted for build/runtime testing; they are not included in the image or committed configuration.
