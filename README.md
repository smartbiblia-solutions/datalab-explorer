# DataLab Explorer

Publish interactive [Keshif](https://github.com/smartbiblia-solutions/keshif-plus-custom) dashboards from a spreadsheet, in the spirit of BRGM Publications Explorer, for any tabular data.

1. **Import** a CSV, TSV, Excel (.xlsx) or JSON file. The separator, encoding and sheet are detected; you see the first rows and the detected columns before anything is saved.
2. **Configure** the dashboard: choose which columns become filters, their label and panel, the multi-value separator (for example `;` in an author list), the type (text, number, year, date) and how records are shown. The real dashboard redraws next to the settings.
3. **Publish** it under an address such as `/v/publications-2025`. The homepage lists the published dashboards; visitors can filter and export their selection as CSV.

A publication is a frozen copy limited to the columns the dashboard uses. Replacing a dataset's file keeps the dashboard settings; public pages change only when you press "Mettre à jour la publication".

## Run locally

Python 3.12+:

```sh
bash scripts/setup.sh
.venv/bin/python -m flask --app app add-user your-name
bash scripts/dev.sh
```

Open http://127.0.0.1:5000 and sign in. Data lives in `instance/` (SQLite database, dataset and publication JSON files, session key); back up that folder.

## Docker

```sh
docker compose up --build -d --wait
docker compose exec web python -m flask --app app add-user your-name
```

Data lives in the `datalab-data` volume. Settings, from your shell or an untracked `.env` file:

| Variable | Default | Purpose |
|---|---|---|
| `DATALAB_TITLE` | `DataLab Explorer` | Site name in the header and homepage |
| `DATALAB_LANG` | `fr` | Default interface language (`fr` or `en`); visitors can switch in the footer |
| `DATALAB_PORT` | `5000` | Host port |
| `DATALAB_BIND_ADDRESS` | `127.0.0.1` | Use `0.0.0.0` only behind a TLS reverse proxy |

## Code

| Path | Content |
|---|---|
| `datalab/tabular.py` | Reading files, detecting separator, encoding and column types |
| `datalab/views.py` | Dashboard configurations (JSON), defaults, validation, published copy |
| `datalab/admin.py`, `public.py`, `auth.py` | Curator pages, public pages, sign-in |
| `datalab/translations/*.json` | Interface texts; add a file to add a language |
| `templates/` | Jinja pages (Bootstrap 5) |
| `static/js/dashboard.js` | Turns a configuration into a Keshif dashboard (shared by editor and public page) |
| `static/js/editor.js`, `public.js` | Dashboard editor, public page |
| `static/keshif/` | Copy of the keshif-plus-custom fork, see `static/keshif/VERSION` |

There is no build step. Tests: `.venv/bin/python -m pytest -q`. Check dashboards by hand in the browser after changing `static/js` or updating Keshif with `bash scripts/update-keshif.sh <commit>`.

`docs/` keeps the original specification documents for reference; this version does not implement them.

## Licence

GNU AGPL v3, see [LICENSE](LICENSE). Keshif+ is © Keshif LLC (`static/keshif/LICENSE`, `NOTICE.md`); Bootstrap is MIT (`static/lib/bootstrap/LICENSE`).
