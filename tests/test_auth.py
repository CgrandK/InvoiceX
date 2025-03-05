import unittest
from app import create_app, db
from app.models import User
from flask import url_for
import os
import tempfile

class AuthTestCase(unittest.TestCase):
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
        
    def tearDown(self):
        """Czyszczenie po testach."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_register_and_login(self):
        """Test rejestracji użytkownika i logowania."""
        # Test rejestracji
        response = self.client.post(
            '/auth/register',
            data={
                'email': 'test@example.com',
                'password': 'password123',
                'password2': 'password123',
                'first_name': 'Test',
                'last_name': 'User',
                'company_name': 'Test Company',
                'tax_id': '1234567890'
            },
            follow_redirects=True
        )
        
        # Sprawdź, czy rejestracja się powiodła i przekierowała do logowania
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Gratulacje, rejestracja', response.data)
        
        # Sprawdź, czy użytkownik został dodany do bazy danych
        user = User.query.filter_by(email='test@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.company_name, 'Test Company')
        self.assertEqual(user.tax_id, '1234567890')
        
        # Test logowania
        response = self.client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'password123',
                'remember_me': False
            },
            follow_redirects=True
        )
        
        # Sprawdź, czy logowanie się powiodło i przekierowało do dashboardu
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Zalogowano pomyślnie', response.data)
        self.assertIn(b'Dashboard', response.data)
        
    def test_login_invalid_credentials(self):
        """Test logowania z nieprawidłowymi danymi."""
        # Utwórz użytkownika
        user = User(
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='User'
        )
        db.session.add(user)
        db.session.commit()
        
        # Test logowania z nieprawidłowym hasłem
        response = self.client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'wrongpassword',
                'remember_me': False
            },
            follow_redirects=True
        )
        
        # Sprawdź, czy logowanie się nie powiodło
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Nieprawid\xc5\x82owy email lub has\xc5\x82o', response.data)
        
        # Test logowania z nieprawidłowym adresem email
        response = self.client.post(
            '/auth/login',
            data={
                'email': 'nonexistent@example.com',
                'password': 'password123',
                'remember_me': False
            },
            follow_redirects=True
        )
        
        # Sprawdź, czy logowanie się nie powiodło
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Nieprawid\xc5\x82owy email lub has\xc5\x82o', response.data)
    
    def test_logout(self):
        """Test wylogowania."""
        # Utwórz użytkownika
        user = User(
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='User'
        )
        db.session.add(user)
        db.session.commit()
        
        # Zaloguj użytkownika
        self.client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'password123',
                'remember_me': False
            }
        )
        
        # Wyloguj użytkownika
        response = self.client.get(
            '/auth/logout',
            follow_redirects=True
        )
        
        # Sprawdź, czy wylogowanie się powiodło
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Wylogowano pomy\xc5\x9blnie', response.data)
        self.assertIn(b'Logowanie', response.data)
    
    def test_protect_routes(self):
        """Test ochrony tras wymagających logowania."""
        # Spróbuj dostępu do chronionych tras bez logowania
        protected_routes = [
            '/dashboard',
            '/client/1',
            '/invoice/create',
            '/reports'
        ]
        
        for route in protected_routes:
            response = self.client.get(route, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Prosz\xc4\x99 zalogowa\xc4\x87 si\xc4\x99', response.data)
    
    def test_profile_update(self):
        """Test aktualizacji profilu użytkownika."""
        # Utwórz i zaloguj użytkownika
        user = User(
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='User'
        )
        db.session.add(user)
        db.session.commit()
        
        self.client.post(
            '/auth/login',
            data={
                'email': 'test@example.com',
                'password': 'password123',
                'remember_me': False
            }
        )
        
        # Zaktualizuj profil
        response = self.client.post(
            '/auth/profile',
            data={
                'first_name': 'Updated',
                'last_name': 'Name',
                'company_name': 'Updated Company',
                'tax_id': '9876543210',
                'address_line1': 'Updated Address',
                'city': 'Updated City',
                'postal_code': '12-345',
                'country': 'Updated Country',
                'phone': '+48 123 456 789'
            },
            follow_redirects=True
        )
        
        # Sprawdź, czy aktualizacja się powiodła
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Profil zaktualizowany pomy\xc5\x9blnie', response.data)
        
        # Sprawdź, czy dane użytkownika zostały zaktualizowane
        user = User.query.filter_by(email='test@example.com').first()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'Name')
        self.assertEqual(user.company_name, 'Updated Company')
        self.assertEqual(user.tax_id, '9876543210')
        self.assertEqual(user.address_line1, 'Updated Address')
        self.assertEqual(user.city, 'Updated City')
        self.assertEqual(user.postal_code, '12-345')
        self.assertEqual(user.country, 'Updated Country')
        self.assertEqual(user.phone, '+48 123 456 789')

if __name__ == '__main__':
    unittest.main()