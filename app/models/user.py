from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager
import uuid

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    company_name = db.Column(db.String(100))
    tax_id = db.Column(db.String(50))  # NIP
    address_line1 = db.Column(db.String(100))
    address_line2 = db.Column(db.String(100))
    city = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    logo = db.Column(db.String(255))  # Ścieżka do pliku logo
    is_active = db.Column(db.Boolean, default=True)
    confirmed = db.Column(db.Boolean, default=False)
    confirmed_on = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    
    def __init__(self, email, password, first_name, last_name, **kwargs):
        self.email = email.lower()
        self.set_password(password)
        self.first_name = first_name
        self.last_name = last_name
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<User {self.email}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company_name': self.company_name,
            'tax_id': self.tax_id,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'postal_code': self.postal_code,
            'country': self.country,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
    def get_total_lending_balance(self):
        """
        Zwraca sumaryczny bilans pożyczek dla użytkownika.
        Dodatni bilans oznacza, że użytkownik ma więcej do odzyskania.
        Ujemny bilans oznacza, że użytkownik ma więcej do oddania.
        """
        from app.models.transaction import Transaction, TransactionType
        
        transactions = Transaction.query.filter_by(user_id=self.id).all()
        
        balance = 0
        for transaction in transactions:
            if transaction.transaction_type == TransactionType.LENT_TO:
                balance += float(transaction.amount)
            elif transaction.transaction_type == TransactionType.BORROWED_FROM:
                balance -= float(transaction.amount)
            elif transaction.transaction_type == TransactionType.REPAID_TO:
                balance -= float(transaction.amount)
            elif transaction.transaction_type == TransactionType.RECEIVED_FROM:
                balance += float(transaction.amount)
        
        return balance