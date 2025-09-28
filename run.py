import os
from dotenv import load_dotenv
from app import create_app, db
from app.models import User

# Załaduj zmienne środowiskowe
load_dotenv()

# Określ konfigurację na podstawie zmiennej środowiskowej
config_name = os.environ.get('FLASK_ENV', 'development')
if config_name == 'production':
    app = create_app('app.config.ProductionConfig')
elif config_name == 'testing':
    app = create_app('app.config.TestingConfig')
else:
    app = create_app('app.config.DevelopmentConfig')

# Dodaj shell context
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User
    }

# Uruchom aplikację, jeśli plik jest uruchamiany bezpośrednio
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))