from app import db

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Opcjonalne pola
    unit = db.Column(db.String(20), default='szt.')  # np. szt., godz., dni
    tax_rate = db.Column(db.Numeric(5, 2))  # Indywidualna stawka podatku dla pozycji
    
    def __init__(self, invoice_id, description, unit_price, quantity=1, **kwargs):
        self.invoice_id = invoice_id
        self.description = description
        self.unit_price = unit_price
        self.quantity = quantity
        self.calculate_total()
        
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __repr__(self):
        return f"<InvoiceItem {self.description}>"
    
    def calculate_total(self):
        """Oblicza wartość pozycji faktury."""
        self.total = self.quantity * self.unit_price
        return self.total
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'description': self.description,
            'quantity': float(self.quantity),
            'unit': self.unit,
            'unit_price': float(self.unit_price),
            'tax_rate': float(self.tax_rate) if self.tax_rate else None,
            'total': float(self.total)
        }