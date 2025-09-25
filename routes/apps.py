from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask_login import login_required, current_user
from forms import CreateApp
from extensions import db
from models import UserApp
import uuid, os, zipfile, io, shutil
from werkzeug.utils import secure_filename

apps_bp = Blueprint('apps', __name__, url_prefix='')

@apps_bp.route('/dashboard')
@login_required
def dashboard():
    form = CreateApp()
    # current_user.apps уже доступен через relationship
    return render_template('dashboard.html', username=current_user.username, form=form)

@apps_bp.route('/api/apps', methods=['GET'])
@login_required
def api_list_apps():
    apps = UserApp.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'app_id': a.app_id, 'app_name': a.app_name, 'created_at': a.created_at.isoformat()} for a in apps])

@apps_bp.route('/index', methods=['POST', 'GET'])
@login_required
def index():
    form = CreateApp()
    if form.validate_on_submit():
        app_name = form.NewApp.data
        try:
            app_id = str(uuid.uuid4())[:8]
            app_path = os.path.join(current_app.config['UPLOAD_FOLDER'], app_id)
            os.makedirs(app_path, exist_ok=True)
            basic_html = "this is you website"
            with open(os.path.join(app_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(basic_html)
            new_app = UserApp(app_id=app_id, app_name=app_name, user_id=current_user.id, path=app_path)
            db.session.add(new_app)
            db.session.commit()
            flash(f'Application \"{app_name}\" created! Link: /sites/{app_id}', 'success')
            return redirect(url_for('apps.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating application: {e}', 'error')
    return render_template('create_app.html', form=form, username=current_user.username)

@apps_bp.route('/upload', methods=['POST'])
@login_required
def upload_files():
    if 'files[]' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('apps.dashboard'))
    files = request.files.getlist('files[]')
    app_id = request.form.get('app_id')
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app_obj:
        flash('Application not found', 'error')
        return redirect(url_for('apps.dashboard'))
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            dst = os.path.join(app_obj.path, filename)
            file.save(dst)
    flash('Files uploaded successfully', 'success')
    return redirect(url_for('apps.dashboard'))

@apps_bp.route('/download/<app_id>')
@login_required
def download_app(app_id):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app_obj:
        flash('Application not found', 'error')
        return redirect(url_for('apps.dashboard'))
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(app_obj.path):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.relpath(file_path, app_obj.path))
    memory_file.seek(0)
    return send_file(memory_file, download_name=f'{app_obj.app_name}.zip', as_attachment=True, mimetype='application/zip')

@apps_bp.route('/download/<app_id>/<path:filename>')
@login_required
def download_file(app_id, filename):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app_obj:
        flash('Application not found', 'error')
        return redirect(url_for('apps.dashboard'))
    file_path = os.path.join(app_obj.path, filename)
    if not os.path.exists(file_path):
        flash('File not found', 'error')
        return redirect(url_for('apps.dashboard'))
    return send_file(file_path, as_attachment=True)

@apps_bp.route('/delete/app/<app_id>', methods=['POST'])
@login_required
def delete_app(app_id):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app_obj:
        flash('Application not found', 'error')
        return redirect(url_for('apps.dashboard'))
    try:
        if os.path.exists(app_obj.path):
            shutil.rmtree(app_obj.path)
        db.session.delete(app_obj)
        db.session.commit()
        flash('Application deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting: {e}', 'error')
    return redirect(url_for('apps.dashboard'))

@apps_bp.route('/delete/file/<app_id>/<path:filename>', methods=['POST'])
@login_required
def delete_file(app_id, filename):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first()
    if not app_obj:
        flash('Application not found', 'error')
        return redirect(url_for('apps.dashboard'))
    file_path = os.path.join(app_obj.path, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('File deleted', 'success')
        else:
            flash('File not found', 'error')
    except Exception as e:
        flash(f'Error deleting: {e}', 'error')
    return redirect(url_for('apps.dashboard'))
