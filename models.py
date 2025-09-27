from collections import namedtuple
from extensions import db
from flask_login import UserMixin
from datetime import timezone, datetime
import os



FileNode = namedtuple('FileNode', ['name', 'is_dir', 'children'])

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
    
    def get_files_tree(self, relative_path=""):
        base_path = os.path.join(self.path, relative_path)
        if not os.path.exists(base_path):
            return []

        def build_tree(path):
            items = []
            for name in sorted(os.listdir(path)):
                full_path = os.path.join(path, name)
                if os.path.isdir(full_path):
                    items.append({
                        "name": name,
                        "is_dir": True,
                        "children": build_tree(full_path)
                    })
                else:
                    items.append({
                        "name": name,
                        "is_dir": False
                    })
            return items

        return build_tree(base_path)