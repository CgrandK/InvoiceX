from datetime import datetime
from app.models import Invoice
from app import db
from flask import current_app

class InvoiceNumberGenerator:
    """
    Klasa odpowiedzialna za generowanie numerów faktur.
    Zapewnia unikalność i zgodność z formatem określonym w konfiguracji.
    """
    
    @staticmethod
    def get_next_number(user_id):
        """
        Generuje następny numer faktury dla danego użytkownika.
        Format numeru jest następujący: FV liczba_porządkowa/MIESIĄC/ROK, np. FV 1/03/2025
        """
        prefix = "FV"
        
        # Pobierz bieżący miesiąc i rok
        now = datetime.now()
        month = now.strftime('%m')
        year = now.strftime('%Y')
        
        # Znajdź ostatnią fakturę dla tego użytkownika z bieżącego miesiąca i roku
        last_invoice = (Invoice.query
                        .filter(Invoice.user_id == user_id)
                        .filter(Invoice.invoice_number.like(f'%/{month}/{year}'))
                        .order_by(Invoice.id.desc())
                        .first())
        
        if last_invoice:
            # Jeśli znaleziono fakturę, wyodrębnij numer i zwiększ o 1
            try:
                parts = last_invoice.invoice_number.split()
                if len(parts) >= 2:
                    number_parts = parts[1].split('/')
                    if len(number_parts) >= 3:
                        last_number = int(number_parts[0])
                        next_number = last_number + 1
                    else:
                        next_number = 1
                else:
                    next_number = 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            # Jeśli nie znaleziono faktury dla bieżącego miesiąca/roku, zacznij od 1
            next_number = 1
        
        # Utwórz nowy numer faktury
        invoice_number = f"{prefix} {next_number}/{month}/{year}"
        
        # Upewnij się, że numer jest unikalny
        while Invoice.query.filter_by(invoice_number=invoice_number).first() is not None:
            next_number += 1
            invoice_number = f"{prefix} {next_number}/{month}/{year}"
        
        return invoice_number
    
    @staticmethod
    def get_custom_number(user_id, prefix=None, number=None, month=None, year=None):
        """
        Generuje niestandardowy numer faktury na podstawie podanych parametrów.
        Jeśli któryś z parametrów nie jest podany, używa wartości domyślnych.
        """
        if prefix is None:
            prefix = "FV"
        
        if number is None:
            number = 1
        
        # Użyj bieżącego miesiąca i roku, jeśli nie podano
        now = datetime.now()
        if month is None:
            month = now.strftime('%m')
        
        if year is None:
            year = now.strftime('%Y')
        
        # Utwórz numer faktury
        invoice_number = f"{prefix} {number}/{month}/{year}"
        
        # Upewnij się, że numer jest unikalny
        counter = 0
        original_number = number
        while Invoice.query.filter_by(invoice_number=invoice_number).first() is not None:
            counter += 1
            number = original_number + counter
            invoice_number = f"{prefix} {number}/{month}/{year}"
            
            # Zabezpieczenie przed nieskończoną pętlą
            if counter > 1000:
                raise ValueError("Nie można wygenerować unikalnego numeru faktury po 1000 próbach.")
        
        return invoice_number