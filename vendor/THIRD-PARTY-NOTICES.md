# Third-party provenance and licensing

Keshif+ copyright Keshif LLC. The retained legacy distribution came from this repository's first commit. Its original checksums and source location are recorded in `keshif/baseline.json`; the source remains recoverable in Git history after archive removal. The fetched upstream LICENSE at revision `f534314d3d80f13fd7b4948479bf5efbe068ce78` is retained unchanged as `keshif/UPSTREAM-LICENSE`.

**Unresolved metadata discrepancy:** upstream LICENSE is BSD-style while that revision's package.json declares `AGPL-3.0-only`. We cannot establish that the inherited local bundle matches that revision or resolve the discrepancy on behalf of the copyright holder. Retain the notices and canonical source; obtain clarification before external redistribution requiring a definitive license determination. This project does not relicense upstream code.

The legacy vendor bundles contain third-party implementations including D3 (ISC), Leaflet (BSD-2-Clause), Supercluster (ISC), DOMPurify (Apache-2.0/MPL-2.0), Popper (MIT), Tippy (MIT), noUiSlider (MIT), Luxon (MIT) and Pikaday (MIT). In-source notices are retained. The source maps retain the original component source context. Exact legacy component versions are not all proven by the available bundle; do not replace provenance uncertainty with guessed package versions.

Font Awesome **Free 5.15.4** is installed through the locked npm dependency. Its license is retained in `FONT-AWESOME-LICENSE.txt` (icons CC BY 4.0, fonts SIL OFL 1.1, code MIT). The build removes inherited font-face declarations and uses this Free build; inherited Pro-named font binaries are excluded. Some Pro-only glyph names may fall back to an absent icon; labeled studio controls remain usable.

Build/test dependencies and their exact versions/integrity hashes are in package-lock.json; Python runtime/test dependencies are pinned in requirements.lock. Applicable package licenses remain with their installed distributions.
