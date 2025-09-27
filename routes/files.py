from flask import Blueprint, send_from_directory, redirect, url_for, make_response
from models import UserApp
import os

files_bp = Blueprint('files', __name__, url_prefix='')

@files_bp.route('/sites/<site_id>')
def show_site_redirect(site_id):
    return redirect(url_for('files.serve_site', site_id=site_id))



@files_bp.route('/sites/<site_id>/', defaults={'filename': 'index.html'})
@files_bp.route('/sites/<site_id>/<path:filename>')
def serve_site(site_id, filename='index.html'):
    app_obj = UserApp.query.filter_by(app_id=site_id).first_or_404()
    response = make_response(send_from_directory(app_obj.path, filename))
    
    # Кэшировать CSS/JS/изображения на 1 час
    
    
    return response

