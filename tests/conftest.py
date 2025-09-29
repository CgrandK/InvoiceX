import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    app = create_app('app.config.TestingConfig')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    user = User(
        email='jan.kowalski@example.com',
        password='bezpiecznehaslo',
        first_name='Jan',
        last_name='Kowalski'
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def authenticated_client(client, user):
    login_response = client.post(
        '/auth/login',
        data={'email': user.email, 'password': 'bezpiecznehaslo'},
        follow_redirects=True
    )
    assert login_response.status_code == 200
    return client
