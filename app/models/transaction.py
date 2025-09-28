# app/models/transaction.py
from datetime import datetime
from app import db
from enum import Enum

class TransactionType(Enum):
    BORROWED_FROM = 1  # Pożyczyłem od (ktoś pożyczył mi)
    LENT_TO = 2        # Pożyczyłem komuś
    RECEIVED_FROM = 3  # Otrzymałem spłatę od
    REPAID_TO = 4      # Oddałem komuś

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relacje
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    contact = db.relationship('Contact', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f'<Transaction {self.id}: {self.transaction_type.name} {self.amount}>'

    @staticmethod
    def get_balance_with_contact(user_id, contact_id):
        """
        Oblicza aktualny bilans finansowy pomiędzy użytkownikiem a kontaktem.
        Dodatni bilans oznacza, że kontakt jest winien użytkownikowi.
        Ujemny bilans oznacza, że użytkownik jest winien kontaktowi.
        """
        transactions = Transaction.query.filter_by(user_id=user_id, contact_id=contact_id).all()

        balance = 0
        for transaction in transactions:
            balance += Transaction.get_balance_delta(transaction.transaction_type, transaction.amount)

        return balance

    @staticmethod
    def get_balance_delta(transaction_type, amount):
        """
        Zwraca zmianę salda dla danego typu transakcji.
        """
        mapping = {
            TransactionType.LENT_TO: 1,
            TransactionType.BORROWED_FROM: -1,
            TransactionType.RECEIVED_FROM: -1,
            TransactionType.REPAID_TO: 1,
        }

        multiplier = mapping.get(transaction_type)
        if multiplier is None:
            return 0

        return multiplier * float(amount)

    @staticmethod
    def get_transaction_history(user_id, contact_id):
        """
        Zwraca historię transakcji pomiędzy użytkownikiem a kontaktem,
        posortowaną od najnowszej do najstarszej.
        """
        return Transaction.query.filter_by(
            user_id=user_id,
            contact_id=contact_id
        ).order_by(Transaction.date.desc()).all()
