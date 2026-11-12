from extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    """
    User model for admin authentication.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class PublishedView(db.Model):
    """
    Model to store information about visualizations made public by the admin.
    """
    id = db.Column(db.Integer, primary_key=True)
    public_name = db.Column(db.String(120), nullable=False)
    data_file = db.Column(db.String(255), nullable=False)
    config_file = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<PublishedView {self.public_name}>'
