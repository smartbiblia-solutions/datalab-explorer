# Implementation status

This is a reconstruction from the specifications in `docs/`, not a restoration of earlier source code.

| Specification area | Status in this reconstruction | Acceptance evidence / boundary |
|---|---|---|
| 1 Product direction | Implemented foundation | Project-based structured-data studio; no mandatory AI service |
| 2 Reuse/evidence | Implemented | Keshif comes from the keshif-plus-custom fork (git history as patch ledger, shared with explore1.portic); licence discrepancy recorded in its NOTICE.md |
| 3 Workspace/journeys | Implemented | Five studios; import → prepare → explore → publish browser journey |
| 4A File sources | Implemented | CSV/TSV strict parsing, quoted fields, XLSX sheets, JSON record path, original upload retained; settings replace a separate pre-import wizard |
| 4A API sources | Implemented bounded subset | GET, page/offset/cursor/next, worker/checkpoints/cancel/restart, bearer reference; deterministic worker tests and separate live OpenAlex smoke |
| 4A Advanced connector options | Deferred | Arbitrary headers, POST opt-in, full response-to-field mapping UI and consistent snapshot resume need connector-specific contracts |
| 4B Preparation | Implemented | 16 declarative operators; whole-dataset errors, previews, strict conversions, version lineage and parent activation |
| 4B Joins/exploding arrays | Deferred | Arrays remain multivalues; relational grain-changing operations require an explicit join/cardinality interface |
| 4C Field dictionary | Implemented core | Union-of-fields profile, labels/type/roles/panels/delimiter, missingness/uniqueness, string natural identities |
| 4C Recommendations | Partial | Conservative default facets; full confidence-based inference and portable mapping suggestions remain future work |
| 4D Dashboard studio | Implemented core | Several saved named layouts, native facets/list/scatter/map, size/color, safe field-token cards; no executable imported callbacks |
| 4D Rich timeseries/provider UI | Deferred | Not offered without a validated timeseries data model or licensed tile-provider setup |
| 4E Inspector/selection | Implemented | Native filters linked by exact IDs, separate table predicates/sort/paging/record details, pinned empty cohorts, coverage counters |
| 4E Geometric semantic replay | Partial | Native gestures retained within a mount; remount/language changes preserve exact IDs as a labeled cohort. Full geometric query serialization and role-change reconciliation are not claimed |
| 4F Reproducibility | Implemented | Versioned manifests, import/export, recipes, dashboards/questions/cohorts pinned to versions, explicit active-version promotion |
| 4F Collaboration/publication | Implemented | Owner/editor/viewer server checks, membership UI, owner protection; explicit reviewed immutable public projection and revocation |
| 5 Differentiators | Implemented subset | Question bookmarks, version differences, coverage lens, saved layout experiments and recipes; recommendation assistant and dedicated rich quality dashboard deferred; inspectable missing-value and IQR outlier cohorts are available |
| 6 Architecture | Implemented | Flask factory, TypeScript adapter, SQLite, durable job table run by an in-process thread, bounded imports, CSRF/access controls |
| 7 Keshif required reliability | Implemented/tested subset | Zero/false inference, missing point geometry, complete clusters, font independence, empty map bounds, resize guards, link-safe list clicks, exact-ID callback; see the fork's history |
| 7 Further renderer proposals | Deferred | Lazy comparison glyphs, optional scatter labels, Canvas renderer and comprehensive scatter rescaling parity need dedicated measurement |
| 8 Delivery phases | Reconciled | Core formerly described implementation reconstructed; advanced proposals remain explicitly scoped above |
| 9 Acceptance matrix | Partial automated coverage | Python tests for server contracts; renderer behaviour is checked by hand. Not every proposed stress/performance/accessibility target is certified |
| Recovery roles / publication / French | Implemented core | Role HTTP tests, projection/stale review/revocation tests, FR/EN common application and native facet interaction |
| Recovery semantic atlas / decision studio / evidence graph | Proposals retained, not claimed as lost delivered code | See extensions.md and the original recovery report |

