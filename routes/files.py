from flask import Blueprint, send_from_directory, redirect, url_for
from models import UserApp
from werkzeug.utils import safe_join
import os

files_bp = Blueprint('files', __name__, url_prefix='')

@files_bp.route('/sites/<site_id>')
def show_site_redirect(site_id):
    return redirect(url_for('files.show_site', site_id=site_id))

@files_bp.route('/sites/<site_id>/')
def show_site(site_id):
    app_obj = UserApp.query.filter_by(app_id=site_id).first_or_404()
    return send_from_directory(app_obj.path, 'index.html')





@files_bp.route('/sites/<site_id>/files/<path:filename>')
def serve_site_file(site_id, filename):
    app_obj = UserApp.query.filter_by(app_id=site_id).first_or_404()
    safe_path = safe_join(app_obj.path, filename)
    if not safe_path or not os.path.exists(safe_path):
        return 'File not found', 404
    return send_from_directory(app_obj.path, filename)

