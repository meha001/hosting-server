from extensions import db
from flask_login import UserMixin
from datetime import timezone, datetime
import os

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    apps = db.relationship('UserApp', backref='owner', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

class UserApp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(8), unique=True, nullable=False)
    app_name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    path = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def get_files(self):
        try:
            if os.path.exists(self.path):
                return os.listdir(self.path)
            return []
        except Exception:
            return []