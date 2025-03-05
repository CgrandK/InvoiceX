import stripe
import paypalrestsdk
from flask import current_app, url_for
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    """
    Klasa odpowiedzialna za integrację z usługami płatności (Stripe i PayPal).
    """
    
    @staticmethod
    def init_stripe():
        """Inicjalizuje połączenie z API Stripe."""
        api_key = current_app.config.get('STRIPE_API_KEY')
        if not api_key:
            raise ValueError("Brak klucza API Stripe w konfiguracji.")
        
        stripe.api_key = api_key
        return stripe
    
    @staticmethod
    def init_paypal():
        """Inicjalizuje połączenie z API PayPal."""
        client_id = current_app.config.get('PAYPAL_CLIENT_ID')
        client_secret = current_app.config.get('PAYPAL_CLIENT_SECRET')
        mode = current_app.config.get('PAYPAL_MODE', 'sandbox')
        
        if not client_id or not client_secret:
            raise ValueError("Brak danych uwierzytelniających PayPal w konfiguracji.")
        
        paypalrestsdk.configure({
            "mode": mode,
            "client_id": client_id,
            "client_secret": client_secret
        })
        
        return paypalrestsdk
    
    @classmethod
    def create_stripe_payment_link(cls, invoice):
        """
        Tworzy link do płatności Stripe dla faktury.
        
        Args:
            invoice: Obiekt faktury do opłacenia
            
        Returns:
            Słownik zawierający link do płatności i ID sesji
        """
        try:
            stripe = cls.init_stripe()
            
            # Utworzenie opisu produktu na podstawie faktury
            description = f"Faktura {invoice.invoice_number}"
            if invoice.user.company_name:
                description += f" - {invoice.user.company_name}"
            
            # Utworzenie sesji płatności
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'pln',
                        'product_data': {
                            'name': description,
                        },
                        'unit_amount': int(float(invoice.total) * 100),  # Kwota w groszach
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=url_for('invoice.payment_success', invoice_id=invoice.id, _external=True),
                cancel_url=url_for('invoice.payment_cancel', invoice_id=invoice.id, _external=True),
                metadata={
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.invoice_number,
                }
            )
            
            return {
                'payment_url': session.url,
                'session_id': session.id
            }
            
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia linku płatności Stripe: {str(e)}")
            raise
    
    @classmethod
    def verify_stripe_payment(cls, session_id):
        """
        Weryfikuje płatność Stripe na podstawie ID sesji.
        
        Args:
            session_id: ID sesji płatności Stripe
            
        Returns:
            True jeśli płatność została zrealizowana, False w przeciwnym razie
        """
        try:
            stripe = cls.init_stripe()
            session = stripe.checkout.Session.retrieve(session_id)
            
            return session.payment_status == 'paid'
            
        except Exception as e:
            logger.error(f"Błąd podczas weryfikacji płatności Stripe: {str(e)}")
            return False
    
    @classmethod
    def create_paypal_payment(cls, invoice):
        """
        Tworzy płatność PayPal dla faktury.
        
        Args:
            invoice: Obiekt faktury do opłacenia
            
        Returns:
            Słownik zawierający link do zatwierdzenia płatności i ID płatności
        """
        try:
            paypal = cls.init_paypal()
            
            # Utworzenie opisu płatności
            description = f"Faktura {invoice.invoice_number}"
            if invoice.user.company_name:
                description += f" - {invoice.user.company_name}"
            
            # Utworzenie płatności
            payment = paypal.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": url_for('invoice.paypal_success', invoice_id=invoice.id, _external=True),
                    "cancel_url": url_for('invoice.paypal_cancel', invoice_id=invoice.id, _external=True)
                },
                "transactions": [{
                    "description": description,
                    "invoice_number": invoice.invoice_number,
                    "amount": {
                        "total": f"{float(invoice.total):.2f}",
                        "currency": "PLN"
                    },
                    "custom": str(invoice.id)
                }]
            })
            
            # Utworzenie płatności
            if payment.create():
                # Znalezienie linku do zatwierdzenia
                for link in payment.links:
                    if link.rel == "approval_url":
                        return {
                            'payment_url': link.href,
                            'payment_id': payment.id
                        }
            
            logger.error("Nie można utworzyć płatności PayPal.")
            return None
            
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia płatności PayPal: {str(e)}")
            raise
    
    @classmethod
    def verify_paypal_payment(cls, payment_id):
        """
        Weryfikuje płatność PayPal na podstawie ID płatności.
        
        Args:
            payment_id: ID płatności PayPal
            
        Returns:
            True jeśli płatność została zrealizowana, False w przeciwnym razie
        """
        try:
            paypal = cls.init_paypal()
            payment = paypalrestsdk.Payment.find(payment_id)
            
            if payment.state == 'approved':
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Błąd podczas weryfikacji płatności PayPal: {str(e)}")
            return False