# Retained Keshif patch ledger

Baseline: repository commit `3090fcf374df7d86aa54c9acb66b25d7ce6d1905`, former `archives/openalex/static/dist`. Exact original SHA-256 values are recorded in `baseline.json`. Upstream notice revision `f534314d3d80f13fd7b4948479bf5efbe068ce78` supplies the upstream LICENSE only; it is **not asserted to be the build revision** of the local bundle.

Canonical source: readable `keshif.js`. `patches.json` retains exact before/after anchors, and `scripts/patch-keshif.py` documents the initial patch procedure. Run `npm run build` after source changes. Generated JS and source maps are never edited by hand.

| Patch | Reason | Evidence |
|---|---|---|
| Strict empty-string inference | `0 == ''` and `false == ''` discarded valid values | Browser directly exercises native inference on zero and false |
| Optional geometry + finite point filtering | Missing geometry must not crash clustering | Browser builds a point index with a missing record |
| Infinite cluster leaf limit | Configured cap truncated exact membership | Browser verifies all 1,201 members |
| No external WebFont import | An optional font request must not block loading | Browser runs using local assets/system fonts |
| List link click guard | Preserve intended anchor navigation | Safe URL/escaped card adapter; native click guard retained |
| Hidden/reentrant resize guard | Avoid hidden-container and recursive geometry updates | Repeated tab/view changes at wide/narrow sizes |
| Configurable central record height | Remove hard-coded 200px reservation | Adapter sets 360px minimum |
| Exact selection callback | Explicit supported adapter hook | Native categorical filter updates table; empty cohort persists |
| Invalid/empty map bounds fallback | No-coordinate map needs a valid initial view | Guard before Leaflet fitBounds |

Inherited duplicate `recordGeo` case in type ordering is harmless and retained (esbuild reports it). Native advanced timeseries and other optional renderer behaviors are not claimed to have received all Portic fixes. The original Portic source/patch report was not uploaded in this task, so no assertion of patch parity is made.

Additional integration corrections found by the reconstruction tests: lazy-load the mapping UMD without overwriting its real global constructor with the empty ES namespace; return the configured constant point size for pin maps without a size field. `scripts/verify-vendor.py` reverses the complete ledger and verifies the resulting baseline hash before every build.
