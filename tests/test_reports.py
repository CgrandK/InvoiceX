import unittest
from app import create_app, db
from app.models import User, Client, Invoice, InvoiceItem, InvoiceStatus
from datetime import datetime, timedelta
import os
import tempfile
import io

class ReportsTestCase(unittest.TestCase):
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
        
        # Utwórz klientów
        self.client1 = Client(
            user_id=self.user.id,
            name='Test Client 1',
            email='client1@example.com',
            company_name='Test Client Company 1',
            tax_id='1234567890'
        )
        self.client2 = Client(
            user_id=self.user.id,
            name='Test Client 2',
            email='client2@example.com',
            company_name='Test Client Company 2',
            tax_id='0987654321'
        )
        db.session.add(self.client1)
        db.session.add(self.client2)
        db.session.commit()
        
        # Utwórz faktury
        today = datetime.utcnow().date()
        
        # Faktura 1 - Styczeń, opłacona
        invoice1 = Invoice(
            user_id=self.user.id,
            client_id=self.client1.id,
            invoice_number='INV/1001/01/2025',
            issue_date=datetime(2025, 1, 15).date(),
            due_date=datetime(2025, 1, 29).date(),
            status=InvoiceStatus.PAID,
            payment_method='bank_transfer',
            tax_rate=23,
            discount=0,
            subtotal=1000,
            tax_amount=230,
            total=1230,
            payment_date=datetime(2025, 1, 20).date()
        )
        
        # Faktura 2 - Luty, oczekująca
        invoice2 = Invoice(
            user_id=self.user.id,
            client_id=self.client1.id,
            invoice_number='INV/1002/02/2025',
            issue_date=datetime(2025, 2, 15).date(),
            due_date=datetime(2025, 2, 29).date(),
            status=InvoiceStatus.PENDING,
            payment_method='bank_transfer',
            tax_rate=23,
            discount=0,
            subtotal=800,
            tax_amount=184,
            total=984
        )
        
        # Faktura 3 - Luty, przeterminowana
        invoice3 = Invoice(
            user_id=self.user.id,
            client_id=self.client2.id,
            invoice_number='INV/1003/02/2025',
            issue_date=datetime(2025, 2, 5).date(),
            due_date=datetime(2025, 2, 10).date(),
            status=InvoiceStatus.OVERDUE,
            payment_method='bank_transfer',
            tax_rate=23,
            discount=0,
            subtotal=500,
            tax_amount=115,
            total=615
        )
        
        db.session.add(invoice1)
        db.session.add(invoice2)
        db.session.add(invoice3)
        db.session.commit()
        
        # Zaloguj użytkownika
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user.id
            sess['_fresh'] = True
    
    def test_reports_index(self):
        """Test strony głównej raportów."""
        response = self.client.get('/reports/')
        
        # Sprawdź, czy strona raportów działa
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Raporty i eksport', response.data)
        
        # Sprawdź, czy pokazuje poprawne statystyki
        self.assertIn(b'3</div>', response.data)  # Łączna liczba faktur
        self.assertIn(b'2</div>', response.data)  # Łączna liczba klientów
    
    def test_monthly_report(self):
        """Test raportu miesięcznego."""
        response = self.client.get('/reports/monthly?year=2025')
        
        # Sprawdź, czy raport miesięczny działa
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Raport miesi\xc4\x99czny - 2025', response.data)
        
        # Sprawdź, czy pokazuje dane dla stycznia
        self.assertIn(b'January', response.data)  # Miesiąc
        self.assertIn(b'1230.00', response.data)  # Suma za styczeń
        
        # Sprawdź, czy pokazuje dane dla lutego
        self.assertIn(b'February', response.data)  # Miesiąc
        self.assertIn(b'1599.00', response.data)  # Suma za luty (984 + 615)
    
    def test_client_report(self):
        """Test raportu klienta."""
        response = self.client.get(f'/reports/client?client_id={self.client1.id}')
        
        # Sprawdź, czy raport klienta działa
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Raport klienta', response.data)
        self.assertIn(f'Test Client 1'.encode(), response.data)
        
        # Sprawdź, czy pokazuje faktury klienta
        self.assertIn(b'INV/1001/01/2025', response.data)
        self.assertIn(b'INV/1002/02/2025', response.data)
        
        # Sprawdź, czy pokazuje poprawne podsumowanie płatności
        self.assertIn(b'1230.00', response.data)  # Zapłacone
        self.assertIn(b'984.00', response.data)   # Oczekujące
    
    def test_export_monthly(self):
        """Test eksportu raportu miesięcznego."""
        # Test eksportu do CSV
        response = self.client.get('/reports/export-monthly?year=2025&format=csv')
        
        # Sprawdź, czy eksport działa
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn('attachment; filename=raport_miesieczny_2025.csv', 
                      response.headers['Content-Disposition'])
        
        # Sprawdź zawartość pliku CSV
        content = response.data.decode('utf-8')
        self.assertIn('January', content)
        self.assertIn('February', content)
        self.assertIn('1230.0', content)  # Suma za styczeń
        self.assertIn('1599.0', content)  # Suma za luty (984 + 615)
        
        # Test eksportu do Excel
        response = self.client.get('/reports/export-monthly?year=2025&format=excel')
        
        # Sprawdź, czy eksport działa
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename=raport_miesieczny_2025.xlsx', 
                      response.headers['Content-Disposition'])
    
    def test_export_client(self):
        """Test eksportu raportu klienta."""
        # Test eksportu do CSV
        response = self.client.get(f'/reports/export-client?client_id={self.client1.id}&format=csv')
        
        # Sprawdź, czy eksport działa
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn('attachment; filename=raport_klienta_Test_Client_1_', 
                      response.headers['Content-Disposition'])
        
        # Sprawdź zawartość pliku CSV
        content = response.data.decode('utf-8')
        self.assertIn('INV/1001/01/2025', content)
        self.assertIn('INV/1002/02/2025', content)
        self.assertIn('1230.0', content)  # Wartość faktury 1
        self.assertIn('984.0', content)   # Wartość faktury 2
        
        # Test eksportu do Excel
        response = self.client.get(f'/reports/export-client?client_id={self.client1.id}&format=excel')
        
        # Sprawdź, czy eksport działa
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename=raport_klienta_Test_Client_1_', 
                      response.headers['Content-Disposition'])
    
    def test_export_all_invoices(self):
        """Test eksportu wszystkich faktur."""
        # Test eksportu do CSV
        response = self.client.get('/reports/export-all-invoices?format=csv')
        
        # Sprawdź, czy eksport działa
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn('attachment; filename=wszystkie_faktury_', 
                      response.headers['Content-Disposition'])
        
        # Sprawdź zawartość pliku CSV
        content = response.data.decode('utf-8')
        self.assertIn('INV/1001/01/2025', content)
        self.assertIn('INV/1002/02/2025', content)
        self.assertIn('INV/1003/02/2025', content)
        self.assertIn('Test Client 1', content)
        self.assertIn('Test Client 2', content)
        
        # Test eksportu do Excel
        response = self.client.get('/reports/export-all-invoices?format=excel')
        
        # Sprawdź, czy eksport działa
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('attachment; filename=wszystkie_faktury_', 
                      response.headers['Content-Disposition'])

if __name__ == '__main__':
    unittest.main()