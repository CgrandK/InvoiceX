from decimal import Decimal
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app, db
from app.models import User, Contact, Transaction
from app.models.transaction import TransactionType


@pytest.fixture
def app_context():
    app = create_app('app.config.TestingConfig')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_total_lending_balance_with_all_transaction_types(app_context):
    user = User(email='test@example.com', password='secret', first_name='Test', last_name='User')
    db.session.add(user)
    db.session.flush()

    contact_one = Contact(user=user, name='Contact One')
    contact_two = Contact(user=user, name='Contact Two')
    db.session.add_all([contact_one, contact_two])
    db.session.flush()

    transactions = [
        Transaction(user=user, contact=contact_one, amount=Decimal('150.00'), transaction_type=TransactionType.LENT_TO),
        Transaction(user=user, contact=contact_one, amount=Decimal('40.00'), transaction_type=TransactionType.BORROWED_FROM),
        Transaction(user=user, contact=contact_one, amount=Decimal('20.00'), transaction_type=TransactionType.RECEIVED_FROM),
        Transaction(user=user, contact=contact_one, amount=Decimal('10.00'), transaction_type=TransactionType.REPAID_TO),
        Transaction(user=user, contact=contact_two, amount=Decimal('80.00'), transaction_type=TransactionType.BORROWED_FROM),
        Transaction(user=user, contact=contact_two, amount=Decimal('30.00'), transaction_type=TransactionType.REPAID_TO),
    ]

    db.session.add_all(transactions)
    db.session.commit()

    total_balance = user.get_total_lending_balance()
    contact_balances = [contact_one.get_balance(), contact_two.get_balance()]

    assert total_balance == pytest.approx(sum(contact_balances))
    assert contact_one.get_balance() == pytest.approx(100.0)
    assert contact_two.get_balance() == pytest.approx(-50.0)

    contacts_with_debt = [c for c in [contact_one, contact_two] if c.get_balance() != 0]
    total_to_receive = sum(c.get_balance() for c in contacts_with_debt if c.get_balance() > 0)
    total_to_pay = sum(abs(c.get_balance()) for c in contacts_with_debt if c.get_balance() < 0)

    assert total_to_receive == pytest.approx(100.0)
    assert total_to_pay == pytest.approx(50.0)
    assert total_balance == pytest.approx(50.0)
