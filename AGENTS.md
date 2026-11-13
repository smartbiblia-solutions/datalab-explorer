# DataLab Explorer development

Flask + Jinja + Bootstrap 5 + plain ES modules; no build step, no Node. Modelled on BRGM Publications Explorer: import a file, configure a Keshif dashboard, publish it.

- Setup: `bash scripts/setup.sh`; run: `bash scripts/dev.sh`; tests: `.venv/bin/python -m pytest -q`. Dashboards are checked by hand in a browser.
- Three objects only: dataset (rows as JSON in `instance/datasets/`), view (JSON configuration), publication (frozen copy in `instance/publications/`, only the columns the view uses). Keep it that simple.
- Configurations are declarative JSON turned into Keshif options by `static/js/dashboard.js`. Never store or run user-supplied JavaScript.
- Data and uploads stay in `instance/`, never in `static/`. Public routes serve only published copies.
- Every POST carries the session CSRF token (form field `csrf_token` or header `X-CSRF-Token`).
- All interface text goes through `datalab/translations/*.json` (`_()` in templates, `window.DATALAB_T` in scripts). French is the reference; keep `en.json` in step.
- Keshif changes go to the keshif-plus-custom fork first, then `bash scripts/update-keshif.sh <commit>`. Never edit `static/keshif` by hand.
