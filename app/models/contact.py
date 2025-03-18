
from app import db
from datetime import datetime

class Contact(db.Model):
    __tablename__ = 'contacts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relacje
    user = db.relationship('User', backref=db.backref('contacts', lazy=True))
    
    def __repr__(self):
        return f'<Contact {self.id}: {self.name}>'

    def get_balance(self):
        """
        Zwraca aktualny bilans finansowy z tym kontaktem.
        """
        from app.models.transaction import Transaction
        return Transaction.get_balance_with_contact(self.user_id, self.id)