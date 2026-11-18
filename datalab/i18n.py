"""Interface translations. French is the default; each language is one JSON file."""

import json
from pathlib import Path
from flask import current_app, request

FOLDER = Path(__file__).parent / "translations"
_cache = {}


def languages():
    return sorted(p.stem for p in FOLDER.glob("*.json"))


def messages(lang):
    if lang not in _cache:
        _cache[lang] = json.loads((FOLDER / f"{lang}.json").read_text(encoding="utf-8"))
    return _cache[lang]


def current_lang():
    lang = request.cookies.get("lang") if request else None
    return lang if lang in languages() else current_app.config["DEFAULT_LANG"]


def translate(key, **params):
    """Look up a key in the current language, then French; fall back to the key itself."""
    text = messages(current_lang()).get(key) or messages("fr").get(key) or key
    return text.format(**params) if params else text


def client_messages():
    """Strings the browser scripts need (keys starting with "js." and "keshif.")."""
    lang = current_lang()
    merged = {**messages("fr"), **messages(lang)}
    return {k: v for k, v in merged.items() if k.startswith(("js.", "keshif."))}
