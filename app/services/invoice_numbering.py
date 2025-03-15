from datetime import datetime
from app.models import Invoice
from app import db
from flask import current_app
import os
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe z pliku .env
load_dotenv()

class InvoiceNumberGenerator:
    """
    Klasa odpowiedzialna za generowanie numerów faktur.
    Zapewnia unikalność i zgodność z formatem określonym w konfiguracji.
    """

    PREFIX = os.getenv("INVOICE_PREFIX", "FV")
    START_NUMBER = int(os.getenv("INVOICE_START_NUMBER", "1"))

    @staticmethod
    def get_next_number(user_id):
        """
        Generuje następny numer faktury dla danego użytkownika.
        Format numeru jest następujący: PREFIX liczba_porządkowa/MIESIĄC/ROK, np. INV- 1000/03/2025
        """
        now = datetime.now()
        month = now.strftime('%m')
        year = now.strftime('%Y')

        # Znajdź ostatnią fakturę dla użytkownika z bieżącego miesiąca i roku
        last_invoice = (Invoice.query
                        .filter(Invoice.user_id == user_id)
                        .filter(Invoice.invoice_number.like(f'%/{month}/{year}'))
                        .order_by(Invoice.id.desc())
                        .first())

        if last_invoice:
            try:
                parts = last_invoice.invoice_number.split()
                if len(parts) >= 2:
                    number_parts = parts[1].split('/')
                    if len(number_parts) >= 3:
                        last_number = int(number_parts[0])
                        next_number = last_number + 1
                    else:
                        next_number = InvoiceNumberGenerator.START_NUMBER
                else:
                    next_number = InvoiceNumberGenerator.START_NUMBER
            except (ValueError, IndexError):
                next_number = InvoiceNumberGenerator.START_NUMBER
        else:
            next_number = InvoiceNumberGenerator.START_NUMBER

        invoice_number = f"{InvoiceNumberGenerator.PREFIX} {next_number}/{month}/{year}"

        while Invoice.query.filter_by(invoice_number=invoice_number).first() is not None:
            next_number += 1
            invoice_number = f"{InvoiceNumberGenerator.PREFIX} {next_number}/{month}/{year}"

        return invoice_number

    @staticmethod
    def get_custom_number(user_id, prefix=None, number=None, month=None, year=None):
        """
        Generuje niestandardowy numer faktury na podstawie podanych parametrów.
        Jeśli któryś z parametrów nie jest podany, używa wartości domyślnych.
        """
        if prefix is None:
            prefix = InvoiceNumberGenerator.PREFIX

        if number is None:
            number = InvoiceNumberGenerator.START_NUMBER

        now = datetime.now()
        if month is None:
            month = now.strftime('%m')

        if year is None:
            year = now.strftime('%Y')

        invoice_number = f"{prefix} {number}/{month}/{year}"

        counter = 0
        original_number = number
        while Invoice.query.filter_by(invoice_number=invoice_number).first() is not None:
            counter += 1
            number = original_number + counter
            invoice_number = f"{prefix} {number}/{month}/{year}"

            if counter > 1000:
                raise ValueError("Nie można wygenerować unikalnego numeru faktury po 1000 próbach.")

        return invoice_number
