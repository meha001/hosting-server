from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask_login import login_required, current_user
from forms import CreateApp
from extensions import db
from models import UserApp
import uuid, os, zipfile, io
from werkzeug.utils import secure_filename
import shutil
import re
apps_bp = Blueprint('apps', __name__, url_prefix='')


# -------------------------
# DASHBOARD
# -------------------------
@apps_bp.route('/dashboard')
@login_required
def dashboard():
    form = CreateApp()
    apps = UserApp.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html',
                           username=current_user.username,
                           form=form,
                           apps=apps)
    
    
# -------------------------
# API: список приложений
# -------------------------
@apps_bp.route('/api/apps', methods=['GET'])
@login_required
def api_list_apps():
    apps = UserApp.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'app_id': a.app_id,
        'app_name': a.app_name,
        'created_at': a.created_at.isoformat()
    } for a in apps])


# -------------------------
# СОЗДАНИЕ ПРИЛОЖЕНИЯ
# -------------------------
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

            # создаём базовый index.html
            with open(os.path.join(app_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write("this is your website")

            # сохраняем в БД
            new_app = UserApp(app_id=app_id, app_name=app_name,
                              user_id=current_user.id, path=app_path)
            db.session.add(new_app)
            db.session.commit()

            flash(f'Application "{app_name}" created! Link: /sites/{app_id}/', 'success')
            return redirect(url_for('apps.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating application: {e}', 'error')

    return render_template('create_app.html', form=form, username=current_user.username)


# -------------------------
# СОЗДАНИЕ ПАПКИ
# -------------------------
@apps_bp.route('/create/folder/<app_id>', methods=['POST'])
@login_required
def create_folder(app_id):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first_or_404()
    parent = request.form.get("parent", "")
    folder_name = request.form.get("folder_name", "").strip()
    
    # Проверка глубины вложенности (макс 5 уровней)
    depth = len([p for p in parent.split("/") if p])
    if depth >= 5:
        flash("Folder nesting limit exceeded (max 5 levels)", "error")
        return redirect(url_for("apps.manage_app", app_id=app_id, path=parent))
    
    #  Проверка на пустое имя или запрещённые символы
    if not folder_name or not re.match(r'^[a-zA-Z0-9_\- ]+$', folder_name):
        flash("Invalid folder name! Use only letters, numbers, spaces, '-' and '_'.", "error")
        return redirect(url_for("apps.manage_app", app_id=app_id, path=parent))


    folder_path = os.path.join(app_obj.path, parent, folder_name)

    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            flash(f'Folder "{folder_name}" created successfully!', 'success')
        else:
            flash(f'Folder "{folder_name}" already exists.', 'warning')
    except Exception as e:
        flash(f'Error creating folder: {e}', 'error')

    return redirect(url_for("apps.manage_app", app_id=app_id, path=parent))


# -------------------------
# ЗАГРУЗКА ФАЙЛОВ
# -------------------------
@apps_bp.route('/upload', methods=['POST'])
@login_required
def upload_files():
    if 'files[]' not in request.files:
        flash('No files selected', 'error')
        return redirect(url_for('apps.manage_app', app_id=request.form.get('app_id')))

    files = request.files.getlist('files[]')
    app_id = request.form.get('app_id')
    current_path = request.form.get("path", "")

    # получаем объект приложения сначала!
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first_or_404()
    upload_path = os.path.join(app_obj.path, current_path)
    os.makedirs(upload_path, exist_ok=True)

    # ---- проверка лимита 100 МБ ----
    MAX_SIZE = 100 * 1024 * 1024  # 100 MB

    def get_folder_size(path):
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
        return total

    current_size = get_folder_size(app_obj.path)
    upload_size = sum(f.content_length or 0 for f in files if f)
    if current_size + upload_size > MAX_SIZE:
        flash("Storage limit exceeded (100 MB)", "error")
        return redirect(url_for("apps.manage_app", app_id=app_id, path=current_path))
    # ---------------------------------

    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            dst_path = os.path.join(upload_path, filename)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            file.save(dst_path)

    flash('Files uploaded successfully', 'success')
    return redirect(url_for('apps.manage_app', app_id=app_id, path=current_path))


# -------------------------
# УДАЛЕНИЕ ФАЙЛА
# -------------------------
@apps_bp.route('/delete/file/<app_id>', methods=['POST'])
@login_required
def delete_file_route(app_id):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first_or_404()
    
    filename = request.form.get('filename', '').strip()  # только имя файла
    current_path = request.form.get('current_path', '')   # путь из URL, например css/

    if not filename:
        flash("No filename provided", "error")
        return redirect(url_for('apps.manage_app', app_id=app_id, path=current_path))

    # Полный путь к файлу
    file_path_abs = os.path.abspath(os.path.join(app_obj.path, current_path, filename))
    app_root = os.path.abspath(app_obj.path)

    # безопасность
    if not file_path_abs.startswith(app_root + os.sep):
        flash("Invalid file path", "error")
        return redirect(url_for('apps.manage_app', app_id=app_id, path=current_path))

    try:
        if os.path.isfile(file_path_abs):
            os.remove(file_path_abs)
            flash("File deleted", "success")
        else:
            flash("File not found", "error")
    except Exception as e:
        current_app.logger.exception("Error deleting file")
        flash(f"Error deleting file: {e}", "error")

    # остаёмся в текущей папке
    return redirect(url_for("apps.manage_app", app_id=app_id, path=current_path))



# -------------------------
# МЕНЕДЖЕР ПРИЛОЖЕНИЯ
# -------------------------
@apps_bp.route('/manage/<app_id>')
@login_required
def manage_app(app_id):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first_or_404()

    current_path = request.args.get("path", "")
    files_tree = app_obj.get_files_tree(current_path)

    return render_template(
        "manage_app.html",
        app=app_obj,
        username=current_user.username,
        current_path=current_path,
        files_tree=files_tree
    )


# -------------------------
# СКАЧАТЬ ВСЁ ПРИЛОЖЕНИЕ ZIP
# -------------------------
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

    return send_file(memory_file,
                     download_name=f'{app_obj.app_name}.zip',
                     as_attachment=True,
                     mimetype='application/zip')


# -------------------------
# СКАЧАТЬ ОТДЕЛЬНЫЙ ФАЙЛ
# -------------------------
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

# -------------------------
# УДАЛЕНИЕ ПРИЛОЖЕНИЕ
# -------------------------
@apps_bp.route('/delete/app/<app_id>', methods=['POST'])
@login_required
def delete_app(app_id):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first_or_404()

    try:
        # удалить папку сайта
        if os.path.exists(app_obj.path):
            
            shutil.rmtree(app_obj.path)

        # удалить из базы
        db.session.delete(app_obj)
        db.session.commit()

        flash(f'Application "{app_obj.app_name}" deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting application: {e}', 'error')

    return redirect(url_for('apps.dashboard'))


# -------------------------
# УДАЛЕНИЕ ПАПКИ
# -------------------------
@apps_bp.route('/delete/folder/<app_id>', methods=['POST'])
@login_required
def delete_folder(app_id):
    app_obj = UserApp.query.filter_by(app_id=app_id, user_id=current_user.id).first_or_404()
    
    foldername = (request.form.get('foldername') or "").strip().lstrip('/')
    current_path = request.form.get('current_path', '')

    if not foldername:
        flash("No folder name provided", "error")
        return redirect(url_for('apps.manage_app', app_id=app_id, path=current_path))

    folder_path = os.path.normpath(os.path.join(app_obj.path, foldername))
    app_root = os.path.abspath(app_obj.path)
    folder_path_abs = os.path.abspath(folder_path)

    # безопасность
    if not (folder_path_abs == app_root or folder_path_abs.startswith(app_root + os.sep)):
        flash("Invalid folder path", "error")
        return redirect(url_for('apps.manage_app', app_id=app_id, path=current_path))

    try:
        if os.path.isdir(folder_path_abs):
            shutil.rmtree(folder_path_abs)
            flash("Folder deleted successfully", "success")
        else:
            flash("Folder not found", "error")
    except Exception as e:
        current_app.logger.exception("Error deleting folder")
        flash(f"Error deleting folder: {e}", "error")

    return redirect(url_for('apps.manage_app', app_id=app_id, path=current_path))
