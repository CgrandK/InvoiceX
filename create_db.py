from app import create_app, db

app = create_app('app.config.DevelopmentConfig')
with app.app_context():
    db.create_all()
    print("Baza danych została pomyślnie utworzona!")