from datetime import datetime
from app import db
import uuid

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    company_name = db.Column(db.String(100))
    tax_id = db.Column(db.String(50))  # NIP
    address_line1 = db.Column(db.String(100))
    address_line2 = db.Column(db.String(100))
    city = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacje
    invoices = db.relationship('Invoice', backref='client', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, user_id, name, **kwargs):
        self.user_id = user_id
        self.name = name
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        return f"<Client {self.name}>"
    
    def get_full_address(self):
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        if self.city and self.postal_code:
            address_parts.append(f"{self.postal_code} {self.city}")
        elif self.city:
            address_parts.append(self.city)
        elif self.postal_code:
            address_parts.append(self.postal_code)
        if self.country:
            address_parts.append(self.country)
        
        return ", ".join(address_parts)
    
    def to_dict(self):
        return {
            'id': self.id,
            'uuid': self.uuid,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'company_name': self.company_name,
            'tax_id': self.tax_id,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'postal_code': self.postal_code,
            'country': self.country,
            'phone': self.phone,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }