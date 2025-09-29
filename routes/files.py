from flask import Blueprint, send_from_directory, redirect, url_for, make_response, abort
from models import UserApp
import os

files_bp = Blueprint('files', __name__, url_prefix='')


@files_bp.route('/sites/<site_id>')
def show_site_redirect(site_id):
    # Редирект на index.html
    return redirect(url_for('files.serve_site', site_id=site_id))


@files_bp.route('/sites/<site_id>/', defaults={'filename': 'index.html'})
@files_bp.route('/sites/<site_id>/<path:filename>')
def serve_site(site_id, filename='index.html'):
    app_obj = UserApp.query.filter_by(app_id=site_id).first_or_404()
    file_path = os.path.join(app_obj.path, filename)

    if not os.path.exists(file_path):
        # Если файла нет, отдаём 404
        abort(404, description=f"File '{filename}' not found in app '{app_obj.app_name}'.")

    response = make_response(send_from_directory(app_obj.path, filename))

    # Кэшировать CSS/JS/изображения на 1 час
    if filename.lower().endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg')):
        response.headers['Cache-Control'] = 'public, max-age=3600'
    else:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

    return response
