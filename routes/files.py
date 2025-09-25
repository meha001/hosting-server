from flask import Blueprint, send_file, abort, current_app
from models import UserApp
import os

files_bp = Blueprint('files', __name__, url_prefix='')

@files_bp.route('/sites/<site_id>')
def show_site(site_id):
    app_obj = UserApp.query.filter_by(app_id=site_id).first()
    if not app_obj:
        return 'Site not found', 404
    index_path = os.path.join(app_obj.path, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    return 'index.html not found', 404

@files_bp.route('/sites/<site_id>/files/<path:filename>')
def serve_site_file(site_id, filename):
    app_obj = UserApp.query.filter_by(app_id=site_id).first()
    if not app_obj:
        return 'Site not found', 404
    file_path = os.path.join(app_obj.path, filename)
    # prevent path traversal
    try:
        abs_base = os.path.abspath(app_obj.path)
        abs_path = os.path.abspath(file_path)
        if not abs_path.startswith(abs_base):
            return 'Forbidden', 403
    except Exception:
        return 'Forbidden', 403
    if os.path.exists(file_path):
        return send_file(file_path)
    return 'File not found', 404
