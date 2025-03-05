from flask import Blueprint, render_template, current_app
from app import db

errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@errors_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@errors_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

# Dodaj blueprint do __init__.py w folderze routes