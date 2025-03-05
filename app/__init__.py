import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from flask_wtf.csrf import CSRFProtect

# Inicjalizacja rozszerzeń
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
jwt = JWTManager()
csrf = CSRFProtect()

def create_app(config_class='app.config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicjalizacja rozszerzeń z aplikacją
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)

    # Konfiguracja Login Managera
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Proszę zalogować się, aby uzyskać dostęp do tej strony.'
    login_manager.login_message_category = 'info'

    # Rejestracja blueprintów
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.invoice import invoice_bp
    from app.routes.reports import reports_bp
    from app.routes.client import client_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(client_bp)


    # Context processor dla wszystkich szablonów
    @app.context_processor
    def utility_processor():
        return {
            'app_name': 'InvoiceX',
            'current_year': 2025
        }

    # Obsługa błędów
    from app.routes import errors
    
    return app