"""Isolated browser-test application; never seeds the actual development database."""

import os
import tempfile

os.environ["DATALAB_INSTANCE"] = tempfile.mkdtemp(prefix="datalab-browser-")
from studio import create_app
from studio.db import db
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db().execute(
        "INSERT INTO users(username,password) VALUES (?,?)",
        ("browser-test", generate_password_hash("browser-test-password")),
    )
    db().commit()
app.run(host="127.0.0.1", port=5101)
