# Architecture and contracts

## Persistence and authorization

`studio.create_app` is the Flask factory. SQLite stores users, projects, membership, immutable versions, typed objects, frozen releases and a durable job queue. Foreign keys are enabled. Schema migration 2 adds memberships and backfills every existing project's owner; `PRAGMA user_version` records the schema and rejects future incompatible databases. Tests construct an actual version-1 database, migrate it twice and check ownership/data preservation. Back up `instance/` before upgrading; no previous lost application's exact schema was available.

Every private route rechecks membership. Owner includes editor/viewer capabilities; editor can import, prepare and author; viewer can inspect/export. Only owner changes membership or publishes/revokes. The original owner cannot be downgraded. Session-backed writes, including login, require a session CSRF token. Original files use generated storage names, independent of uploaded filenames. Data and API pages are never exposed through the static route.

A dataset version contains normalized records, the union-of-fields profile, input lineage, preparation recipe and private source metadata. Object kinds are dictionary, dashboard, recipe, cohort and snapshot. Dictionaries/dashboards are version-scoped objects, not mutations of dataset rows. Recipe application creates a new version only after full-dataset validation. User-provided configuration is JSON; the adapter supplies trusted closures. No user JavaScript is evaluated.

## Worker

Run one worker per installation. Claiming is transactional (`BEGIN IMMEDIATE`). Jobs expose queued, running, cancelled, failed and succeeded states; checkpoints include pages and record counts. Every successful raw response page is retained under a managed job directory. Interrupted running jobs older than five minutes are marked failed on worker startup; explicit retry restarts from page one because mutable APIs cannot guarantee resumable snapshots. Cancellation is checked between bounded requests/pages and atomically before saving the final version. It cannot interrupt an in-progress socket read immediately.

HTTPS destination policy is a server-managed exact host allowlist, with rejection of internal names and private/reserved resolved addresses. Recheck every redirect, retain TLS verification, remove authorization on cross-host redirect. Cloud proxy DNS can work when local DNS cannot; in that case exact administrator host allowlisting is the boundary. Administrators must only allow trusted APIs, never attacker-controlled rebinding hosts. GET only; no automatic mutating query replay. Timeouts are 10s connect / 30s read, at most 8 MiB per page, 100 pages, 30,000 rows, 120s job budget checked between pages. Transient 429/502/503/504 responses have three attempts and honor short Retry-After delays; a longer requested pause fails with restart guidance.

A finite page/record limit fails with an actionable error rather than silently presenting truncated data as complete. Generic page/offset pagination uses `per_page`; APIs with other size conventions can include their own query parameter in the URL. Cursor and next-link modes use an explicit nested next path. Bearer secret references remain server-side. Query-string API keys and custom/mutating authentication flows are not supported. No live refresh is promoted over an existing active version without user activation.

## Selection and rendering

The retained Keshif renderer emits exact included record IDs after filtering. `KeshifAdapter` intersects this with independent table predicates. A pinned selection installs a native Keshif filter, including for an empty ID set. Language changes/remounts retain exact IDs. Question snapshots store those IDs, table predicates, dashboard configuration and note with the immutable version. They are pinned evidence, not automatically re-evaluated live queries. Native filter gestures work inside one mounted dashboard; remounting deliberately preserves their membership as an exact cohort rather than pretending to reconstruct every geometric filter.

The table is a small native TypeScript table (50-row pages) rather than Tabulator. This avoids an additional runtime and keeps the selection contract explicit. Keshif remains the actual facet/scatter/map engine. Map baselayers are disabled by default so the studio runs without a tile-provider credential or network connection. Valid coordinates, including zeros, render; coverage counts identify excluded/missing pairs and overlaps. No sampling or hidden row dropping is performed. Browser datasets above 30,000 rows are rejected with guidance to import an explicit extract.

Public readers load only a frozen projected release. Profiles are recomputed after projection, config is allowlisted/field-validated, all private IDs are replaced, and no source configuration, paths, membership, annotations or private version ID is sent. Preview and confirmation compute the same canonical digest; modifying the projection invalidates the review. No publish-on-preview side effect. Editing private data cannot alter a release. Revocation applies to HTML, data and export routes.

## Custom renderer

Canonical patches are applied to readable `vendor/keshif/keshif.js`, then esbuild creates the minified module and corresponding source map. Local vendor imports and assets are copied into the standalone output. A static SHA-256 manifest inventories the build. `patches.json` records exact before/after anchors. The patch helper is for restoring the original baseline; do not run it again against an already patched file. Rebuild on every canonical source change.
