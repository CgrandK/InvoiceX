from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.invoice import invoice_bp
from app.routes.reports import reports_bp
from app.routes.client import client_bp
from app.routes.errors import errors_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'invoice_bp',
    'reports_bp',
    'client_bp',
    'errors_bp'
]