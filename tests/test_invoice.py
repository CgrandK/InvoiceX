import unittest
from app import create_app, db
from app.models import User, Client, Invoice, InvoiceItem, InvoiceStatus
from flask_login import current_user
from datetime import datetime, timedelta
import os
import tempfile

class InvoiceTestCase(unittest.TestCase):
    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app('app.config.TestingConfig')
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + self.db_path
        self.app.config['WTF_CSRF_ENABLED'] = False  # Wyłączenie CSRF dla testów
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        
        # Przygotuj dane testowe
        self._create_test_data()
        
    def tearDown(self):
        """Czyszczenie po testach."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _create_test_data(self):
        """Przygotowanie danych testowych."""
        # Utwórz użytkownika
        self.user = User(
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='User'
        )
        db.session.add(self.user)
        db.session.commit()
        
        # Utwórz klienta
        self.client_data = Client(
            user_id=self.user.id,
            name='Test Client',
            email='client@example.com',
            company_name='Test Client Company',
            tax_id='1234567890'
        )
        db.session.add(self.client_data)
        db.session.commit()
        
        # Zaloguj użytkownika
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id
            sess['_fresh'] = True
    
    def test_invoice_creation(self):
        """Test tworzenia faktury."""
        # Utwórz fakturę
        today = datetime.utcnow().date()
        due_date = today + timedelta(days=14)
        
        response = self.client.post(
            '/invoice/create',
            data={
                'invoice_number': 'INV/1001/02/2025',
                'client_id': self.client_data.id,
                'issue_date': today.strftime('%Y-%m-%d'),
                'due_date': due_date.strftime('%Y-%m-%d'),
                'payment_method': 'bank_transfer',
                'status': 'draft',
                'tax_rate': 23,
                'discount': 0,
                'items-0-description': 'Test Item',
                'items-0-quantity': 1,
                'items-0-unit': 'szt.',
                'items-0-unit_price': 100,
                'items-0-tax_rate': 23
            },
            follow_redirects=True
        )
        
        # Sprawdź, czy faktura została utworzona
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Faktura zosta\xc5\x82a utworzona', response.data)
        
        # Sprawdź, czy faktura została dodana do bazy danych
        invoice = Invoice.query.filter_by(invoice_number='INV/1001/02/2025').first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.client_id, self.client_data.id)
        self.assertEqual(invoice.status, 'draft')
        self.assertEqual(float(invoice.subtotal), 100.0)
        self.assertEqual(float(invoice.tax_amount), 23.0)
        self.assertEqual(float(invoice.total), 123.0)
        
        # Sprawdź, czy pozycja faktury została dodana
        self.assertEqual(invoice.items.count(), 1)
        item = invoice.items.first()
        self.assertEqual(item.description, 'Test Item')
        self.assertEqual(float(item.quantity), 1.0)
        self.assertEqual(item.unit, 'szt.')
        self.assertEqual(float(item.unit_price), 100.0)
        self.assertEqual(float(item.total), 100.0)
    
    def test_invoice_edit(self):
        """Test edycji faktury."""
        # Utwórz fakturę
        today = datetime.utcnow().date()
        due_date = today + timedelta(days=14)
        
        invoice = Invoice(
            user_id=self.user.id,
            client_id=self.client_data.id,
            invoice_number='INV/1001/02/2025',
            issue_date=today,
            due_date=due_date,
            status=InvoiceStatus.DRAFT,
            payment_method='bank_transfer',
            tax_rate=23,
            discount=0
        )
        db.session.add(invoice)
        db.session.flush()
        
        item = InvoiceItem(
            invoice_id=invoice.id,
            description='Test Item',
            quantity=1,
            unit='szt.',
            unit_price=100,
            tax_rate=23
        )
        db.session.add(item)
        db.session.commit()
        
        invoice.calculate_totals()
        db.session.commit()
        
        # Edytuj fakturę
        response = self.client.post(
            f'/invoice/{invoice.id}/edit',
            data={
                'invoice_number': 'INV/1001/02/2025',
                'client_id': self.client_data.id,
                'issue_date': today.strftime('%Y-%m-%d'),
                'due_date': due_date.strftime('%Y-%m-%d'),
                'payment_method': 'bank_transfer',
                'status': 'pending',
                'tax_rate': 23,
                'discount': 10,
                'items-0-description': 'Updated Item',
                'items-0-quantity': 2,
                'items-0-unit': 'szt.',
                'items-0-unit_price': 150,
                'items-0-tax_rate': 23
            },
            follow_redirects=True
        )
        
        # Sprawdź, czy faktura została zaktualizowana
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Faktura zosta\xc5\x82a zaktualizowana', response.data)
        
        # Sprawdź, czy dane faktury zostały zaktualizowane
        invoice = Invoice.query.filter_by(invoice_number='INV/1001/02/2025').first()
        self.assertEqual(invoice.status, 'pending')
        self.assertEqual(float(invoice.discount), 10.0)
        self.assertEqual(float(invoice.subtotal), 300.0)  # 2 * 150
        self.assertEqual(float(invoice.tax_amount), 69.0)  # 300 * 0.23
        self.assertEqual(float(invoice.total), 359.0)  # 300 + 69 - 10
        
        # Sprawdź, czy pozycja faktury została zaktualizowana
        self.assertEqual(invoice.items.count(), 1)
        item = invoice.items.first()
        self.assertEqual(item.description, 'Updated Item')
        self.assertEqual(float(item.quantity), 2.0)
        self.assertEqual(float(item.unit_price), 150.0)
        self.assertEqual(float(item.total), 300.0)
    
    def test_invoice_mark_as_paid(self):
        """Test oznaczania faktury jako opłaconej."""
        # Utwórz fakturę
        today = datetime.utcnow().date()
        due_date = today + timedelta(days=14)
        
        invoice = Invoice(
            user_id=self.user.id,
            client_id=self.client_data.id,
            invoice_number='INV/1001/02/2025',
            issue_date=today,
            due_date=due_date,
            status=InvoiceStatus.PENDING,
            payment_method='bank_transfer',
            tax_rate=23,
            discount=0,
            subtotal=100,
            tax_amount=23,
            total=123
        )
        db.session.add(invoice)
        db.session.commit()
        
        # Oznacz fakturę jako opłaconą
        payment_date = today.strftime('%Y-%m-%d')
        response = self.client.post(
            f'/invoice/{invoice.id}/mark-as-paid',
            data={
                'payment_date': payment_date,
                'payment_id': 'TEST123'
            },
            follow_redirects=True
        )
        
        # Sprawdź, czy status faktury został zmieniony
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Faktura zosta\xc5\x82a oznaczona jako op\xc5\x82acona', response.data)
        
        # Sprawdź, czy dane faktury zostały zaktualizowane
        invoice = Invoice.query.filter_by(invoice_number='INV/1001/02/2025').first()
        self.assertEqual(invoice.status, InvoiceStatus.PAID)
        self.assertEqual(invoice.payment_date.strftime('%Y-%m-%d'), payment_date)
        self.assertEqual(invoice.payment_id, 'TEST123')
    
    def test_invoice_download(self):
        """Test pobierania faktury w formacie PDF."""
        # Utwórz fakturę
        today = datetime.utcnow().date()
        due_date = today + timedelta(days=14)
        
        invoice = Invoice(
            user_id=self.user.id,
            client_id=self.client_data.id,
            invoice_number='INV/1001/02/2025',
            issue_date=today,
            due_date=due_date,
            status=InvoiceStatus.PENDING,
            payment_method='bank_transfer',
            tax_rate=23,
            discount=0,
            subtotal=100,
            tax_amount=23,
            total=123
        )
        db.session.add(invoice)
        db.session.commit()
        
        # Pobierz fakturę
        response = self.client.get(f'/invoice/{invoice.id}/download')
        
        # Sprawdź, czy pobieranie działa
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertIn('attachment; filename=Faktura_INV_1001_02_2025.pdf', 
                     response.headers['Content-Disposition'])
    
    def test_invoice_delete(self):
        """Test usuwania faktury."""
        # Utwórz fakturę
        today = datetime.utcnow().date()
        due_date = today + timedelta(days=14)
        
        invoice = Invoice(
            user_id=self.user.id,
            client_id=self.client_data.id,
            invoice_number='INV/1001/02/2025',
            issue_date=today,
            due_date=due_date,
            status=InvoiceStatus.DRAFT,
            payment_method='bank_transfer',
            tax_rate=23,
            discount=0,
            subtotal=100,
            tax_amount=23,
            total=123
        )
        db.session.add(invoice)
        db.session.commit()
        
        # Usuń fakturę
        response = self.client.post(
            f'/invoice/{invoice.id}/delete',
            follow_redirects=True
        )
        
        # Sprawdź, czy faktura została usunięta
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Faktura zosta\xc5\x82a usuni\xc4\x99ta', response.data)
        
        # Sprawdź, czy faktura została usunięta z bazy danych
        invoice = Invoice.query.filter_by(invoice_number='INV/1001/02/2025').first()
        self.assertIsNone(invoice)

if __name__ == '__main__':
    unittest.main()