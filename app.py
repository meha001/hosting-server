from flask import Flask, render_template, url_for, redirect, flash, request, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, Regexp
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from datetime import timezone, datetime
import os
import uuid
import zipfile
import io
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'rkmlkmkklmfmrmgrg'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    apps = db.relationship('UserApp', backref='owner', lazy=True)
    def __repr__(self):
        return f'<User {self.username}>'

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={'placeholder': 'Username'})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField("Register")
    
    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError("That username already exists. Please choose a different one.")

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={'placeholder': 'Username'})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                             render_kw={'placeholder': 'Password'})
    submit = SubmitField("Login")


@app.route('/home')
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            new_user = User(username=form.username.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
    return render_template('register.html', form=form)

#-------------------SYSTEM_ZONE---------------------------------------------#
class CreateApp(FlaskForm):
    NewApp = StringField(validators=[
        InputRequired(),
        Length(min=4, max=20),
        Regexp('^[a-zA-Z0-9_-]+$', message='Only letters, numbers, hyphens, and underscores')
    ], render_kw={'placeholder': 'New app'})
    
    submit = SubmitField('Create')
    
class UserApp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(8), unique=True, nullable=False)
    app_name = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    path = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def get_files(self):
        try:
            if os.path.exists(self.path):
                return os.listdir(self.path)
            return []
        except:
            return []

@app.route('/dashboard')
@login_required
def dashboard():
    form = CreateApp()
    return render_template('dashboard.html', username=current_user.username, form=form)

@app.route('/index', methods=['POST', 'GET'])
@login_required
def index():
    form = CreateApp()
    if form.validate_on_submit():
        app_name = form.NewApp.data
        try:
            # Generate a unique ID for the app
            app_id = str(uuid.uuid4())[:8]
            # Path to the app folder
            app_path = os.path.join('user_files', app_id)
            # Create the folder if it doesn't exist
            os.makedirs(app_path, exist_ok=True)
            # Create a basic index.html
            basic_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{app_name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    h1 {{ color: #333; }}
                </style>
            </head>
            <body>
                <h1>Hello! This is your application "{app_name}"</h1>
                <p>Replace the content of this file with your code!</p>
            </body>
            </html>
            """
            # Save index.html
            with open(os.path.join(app_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(basic_html)
            # Save app info in the database
            new_app = UserApp(
                app_id=app_id,
                app_name=app_name,
                user_id=current_user.id,
                path=app_path
            )
            db.session.add(new_app)
            db.session.commit()
            flash(f'Application "{app_name}" created! Link: /sites/{app_id}', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error creating application: {str(e)}', 'error')
    return render_template('create_app.html', form=form, username=current_user.username)


@app.route('/sites/<site_id>')
def show_site(site_id):
    # Find app by ID
    app = UserApp.query.filter_by(app_id=site_id).first_or_404()
    # Path to index.html
    index_path = os.path.join(app.path, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    else:
        return "index.html not found", 404

@app.route('/upload', methods=['POST'])
@login_required
def upload_files():
    if 'files[]' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('dashboard'))
    files = request.files.getlist('files[]')
    app_id = request.form.get('app_id')  # App ID for upload
    app = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app:
        flash('Application not found', 'error')
        return redirect(url_for('dashboard'))
    for file in files:
        if file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.path, filename)
            file.save(file_path)
    flash('Files uploaded successfully', 'success')
    return redirect(url_for('dashboard'))

@app.route('/download/<app_id>')
@login_required
def download_app(app_id):
    app = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app:
        flash('Application not found', 'error')
        return redirect(url_for('dashboard'))
    # Create ZIP in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(app.path):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.relpath(file_path, app.path))
    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name=f'{app.app_name}.zip',
        as_attachment=True,
        mimetype='application/zip'
    )

@app.route('/download/<app_id>/<filename>')
@login_required
def download_file(app_id, filename):
    app = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app:
        flash('Application not found', 'error')
        return redirect(url_for('dashboard'))
    file_path = os.path.join(app.path, filename)
    if not os.path.exists(file_path):
        flash('File not found', 'error')
        return redirect(url_for('dashboard'))
    return send_file(file_path, as_attachment=True)

@app.route('/delete/app/<app_id>', methods=['POST'])
@login_required
def delete_app(app_id):
    app = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app:
        flash('Application not found', 'error')
        return redirect(url_for('dashboard'))
    try:
        # Delete folder with files
        if os.path.exists(app.path):
            shutil.rmtree(app.path)
        # Delete record from database
        db.session.delete(app)
        db.session.commit()
        flash('Application deleted', 'success')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'error')
    return redirect(url_for('dashboard'))

@app.route('/delete/file/<app_id>/<filename>', methods=['POST'])
@login_required
def delete_file(app_id, filename):
    app = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app:
        flash('Application not found', 'error')
        return redirect(url_for('dashboard'))
    try:
        file_path = os.path.join(app.path, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('File deleted', 'success')
        else:
            flash('File not found', 'error')
    except Exception as e:
        flash(f'Error deleting: {str(e)}', 'error')
    return redirect(url_for('dashboard'))

#---------------------------------------------------------------------------#
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Tables in database: {tables}")
    app.run(debug=True)