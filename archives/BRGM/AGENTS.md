# AGENTS.md - Development Guide for BRGM Publications Explorer

## Commands
- **Run dev server**: `python app.py` (Flask app on port 5000)
- **Initialize database**: `flask init-db`
- **Create admin user**: `flask add-user <username> <password>`
- **Install dependencies**: `pip install -r requirements.txt`
- **No tests found** - Add test framework and update this file

## Architecture
- **Flask app** with modular blueprint structure in `modules/`
- **SQLite database** (`instance/app.db`) with User and PublishedView models
- **Modular design**: public, admin, auth, embedding_atlas, playground_lab, playground_generic
- **Data flow**: Upload CSV/Excel/JSON → Process → Store as JSON → Visualize
- **Static files**: `static/` (configs, data uploads, CSS, JS, images)
- **Templates**: `templates/` (main) + module-specific templates

## Code Style
- **Import order**: Flask imports, extensions, standard library, local imports
- **Function style**: Docstrings for routes, snake_case naming
- **Error handling**: Try/catch with JSON error responses
- **Database**: SQLAlchemy ORM with extensions pattern (no circular imports)
- **Blueprint registration**: Conditional module loading via config flags
- **File processing**: Pandas for data transformation, JSON for storage
- **Template injection**: Global config context processor
