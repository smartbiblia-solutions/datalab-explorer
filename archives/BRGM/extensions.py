from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

# Initialize extensions so they can be imported by other modules
# without causing circular imports with the app factory.
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
