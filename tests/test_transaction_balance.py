import os
import sys
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.contact import Contact
from app.models.transaction import Transaction, TransactionType
from app.models.user import User


@pytest.fixture
def app_context():
    app = create_app('app.config.TestingConfig')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_balance_with_all_transaction_types(app_context):
    user = User(email='john@example.com', password='secret', first_name='John', last_name='Doe')
    contact = Contact(user=user, name='Jane Doe')

    db.session.add(user)
    db.session.add(contact)
    db.session.commit()

    transactions = [
        Transaction(
            user_id=user.id,
            contact_id=contact.id,
            amount=Decimal('100.00'),
            transaction_type=TransactionType.LENT_TO,
        ),
        Transaction(
            user_id=user.id,
            contact_id=contact.id,
            amount=Decimal('50.00'),
            transaction_type=TransactionType.BORROWED_FROM,
        ),
        Transaction(
            user_id=user.id,
            contact_id=contact.id,
            amount=Decimal('30.00'),
            transaction_type=TransactionType.RECEIVED_FROM,
        ),
        Transaction(
            user_id=user.id,
            contact_id=contact.id,
            amount=Decimal('20.00'),
            transaction_type=TransactionType.REPAID_TO,
        ),
    ]

    db.session.add_all(transactions)
    db.session.commit()

    expected_balance = 40.0

    assert Transaction.get_balance_with_contact(user.id, contact.id) == pytest.approx(expected_balance)
    assert contact.get_balance() == pytest.approx(expected_balance)
