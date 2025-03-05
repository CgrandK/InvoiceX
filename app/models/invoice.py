from datetime import datetime, timedelta
from app import db
import uuid

class InvoiceStatus:
    DRAFT = 'draft'
    PENDING = 'pending'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELED = 'canceled'
    
    @classmethod
    def all(cls):
        return [cls.DRAFT, cls.PENDING, cls.PAID, cls.OVERDUE, cls.CANCELED]

class PaymentMethod:
    BANK_TRANSFER = 'bank_transfer'
    CASH = 'cash'
    CREDIT_CARD = 'credit_card'
    PAYPAL = 'paypal'
    STRIPE = 'stripe'
    OTHER = 'other'
    
    @classmethod
    def all(cls):
        return [cls.BANK_TRANSFER, cls.CASH, cls.CREDIT_CARD, cls.PAYPAL, cls.STRIPE, cls.OTHER]

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    
    invoice_number = db.Column(db.String(50), nullable=False, unique=True)
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    due_date = db.Column(db.Date, nullable=False, 
                          default=lambda: (datetime.utcnow() + timedelta(days=14)).date())
    
    status = db.Column(db.String(20), nullable=False, default=InvoiceStatus.DRAFT)
    payment_method = db.Column(db.String(20), default=PaymentMethod.BANK_TRANSFER)
    
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), default=0)  # Procent podatku
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    
    notes = db.Column(db.Text)
    terms = db.Column(db.Text)
    
    payment_date = db.Column(db.Date)
    payment_id = db.Column(db.String(100))  # ID transakcji z systemu płatności
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacje
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', 
                            cascade='all, delete-orphan')
    
    def __init__(self, user_id, client_id, invoice_number, **kwargs):
        self.user_id = user_id
        self.client_id = client_id
        self.invoice_number = invoice_number
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"
    
    def calculate_totals(self):
        """Oblicza wartości faktury na podstawie pozycji faktury."""
        self.subtotal = sum(item.total for item in self.items)
        self.tax_amount = (self.subtotal * self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount - self.discount
        return self.total
    
    def is_overdue(self):
        """Sprawdza, czy faktura jest przeterminowana."""
        return (not self.status == InvoiceStatus.PAID and 
                self.due_date < datetime.utcnow().date())
    
    def update_status(self):
        """Aktualizuje status faktury na podstawie dat i płatności."""
        if self.status == InvoiceStatus.CANCELED:
            return self.status
        
        if self.status == InvoiceStatus.PAID:
            return self.status
        
        if self.is_overdue():
            self.status = InvoiceStatus.OVERDUE
        elif self.status == InvoiceStatus.DRAFT:
            pass
        else:
            self.status = InvoiceStatus.PENDING
        
        return self.status
    
    def mark_as_paid(self, payment_date=None, payment_id=None):
        """Oznacza fakturę jako zapłaconą."""
        self.status = InvoiceStatus.PAID
        self.payment_date = payment_date or datetime.utcnow().date()
        if payment_id:
            self.payment_id = payment_id
        return True
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'user_id': self.user_id,
            'client_id': self.client_id,
            'invoice_number': self.invoice_number,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'payment_method': self.payment_method,
            'subtotal': float(self.subtotal),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'discount': float(self.discount),
            'total': float(self.total),
            'notes': self.notes,
            'terms': self.terms,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_id': self.payment_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items]
        }