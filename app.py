from flask import Flask
from extensions import db, bcrypt, login_manager
from routes.auth import auth_bp
from routes.apps import apps_bp
from routes.files import files_bp
import os
from config import Config

def create_app(config_class = Config):
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(config_class)

    # init extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(apps_bp)
    app.register_blueprint(files_bp)

    # ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        print('Database tables created successfully')
    app.run(debug=True)