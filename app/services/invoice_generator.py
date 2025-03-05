from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
import os
import io
from datetime import datetime
from flask import current_app

# Rejestrowanie fontów (opcjonalnie)
try:
    fonts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static/fonts')
    if not os.path.exists(fonts_dir):
        print("Brak czcionek!!")

    # Ścieżki do czcionek
    dejavu_path = os.path.join(fonts_dir, 'DejaVuSans.ttf')
    dejavu_bold_path = os.path.join(fonts_dir, 'DejaVuSans-Bold.ttf')


    pdfmetrics.registerFont(TTFont('DejaVuSans', dejavu_path))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', dejavu_bold_path))
    FONT_NAME = 'DejaVuSans'
except:
    FONT_NAME = 'Helvetica'
    
class InvoicePDFGenerator:
    def __init__(self, invoice, user, client):
        self.invoice = invoice
        self.user = user
        self.client = client
        self.buffer = io.BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        
    def _setup_styles(self):
        """Konfiguruje style dla dokumentu PDF."""
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            fontName=FONT_NAME,
            fontSize=16,
            leading=20,
            alignment=TA_LEFT,
            textColor=colors.black,
            spaceAfter=6))
            
        self.styles.add(ParagraphStyle(
            name='InvoiceInfo',
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT))
            
        self.styles.add(ParagraphStyle(
            name='AddressTitle',
            fontName=FONT_NAME,
            fontSize=10,
            leading=12,
            alignment=TA_LEFT,
            textColor=colors.gray))
            
        self.styles.add(ParagraphStyle(
            name='Address',
            fontName=FONT_NAME,
            fontSize=10,
            leading=12,
            alignment=TA_LEFT))
            
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            fontName=FONT_NAME + '-Bold' if FONT_NAME != 'Helvetica' else 'Helvetica-Bold',
            fontSize=9,
            leading=12,
            alignment=TA_LEFT))
            
        self.styles.add(ParagraphStyle(
            name='TableCell',
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT))
            
        self.styles.add(ParagraphStyle(
            name='TableCellRight',
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            alignment=TA_RIGHT))
            
        self.styles.add(ParagraphStyle(
            name='Total',
            fontName=FONT_NAME + '-Bold' if FONT_NAME != 'Helvetica' else 'Helvetica-Bold',
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT))
            
        self.styles.add(ParagraphStyle(
            name='Notes',
            fontName=FONT_NAME,
            fontSize=9,
            leading=12,
            alignment=TA_LEFT))
    
    def generate(self):
        """Generuje dokument PDF faktury."""
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Faktura {self.invoice.invoice_number}"
        )
        
        # Lista elementów, które zostaną dodane do dokumentu
        elements = []
        
        # Dodaj header faktury
        self._add_header(elements)
        
        # Dodaj informacje o wystawcy i odbiorcy
        self._add_addresses(elements)
        
        # Dodaj informacje o fakturze
        self._add_invoice_info(elements)
        
        # Dodaj tabelę z pozycjami faktury
        self._add_items_table(elements)
        
        # Dodaj podsumowanie
        self._add_summary(elements)
        
        # Dodaj notatki i warunki
        self._add_notes(elements)
        
        # Dodaj stopkę
        self._add_footer(elements)
        
        # Zbuduj dokument
        doc.build(elements)
        
        # Pobierz zawartość bufora
        self.buffer.seek(0)
        return self.buffer
    
    def _add_header(self, elements):
        """Dodaje nagłówek faktury."""
        # Tytuł faktury
        elements.append(Paragraph(f"Faktura {self.invoice.invoice_number}", self.styles['InvoiceTitle']))
        elements.append(Spacer(1, 6*mm))
        
        # Logo firmy (jeśli dostępne)
        if self.user.logo and os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], self.user.logo)):
            logo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], self.user.logo)
            img = Image(logo_path, width=4*cm, height=2*cm)
            img.hAlign = 'LEFT'
            elements.append(img)
            elements.append(Spacer(1, 5*mm))
    
    def _add_addresses(self, elements):
        """Dodaje informacje o wystawcy i odbiorcy faktury."""
        # Tabela z danymi wystawcy i odbiorcy
        data = [
            [Paragraph("Sprzedawca:", self.styles['AddressTitle']), 
             Paragraph("Nabywca:", self.styles['AddressTitle'])],
            
            [Paragraph(self.user.company_name or self.user.get_full_name(), self.styles['Address']),
             Paragraph(self.client.company_name or self.client.name, self.styles['Address'])]
        ]
        
        # Dodaj NIP wystawcy jeśli dostępny
        if self.user.tax_id:
            data[1][0] = Paragraph(
                f"{self.user.company_name or self.user.get_full_name()}<br/>NIP: {self.user.tax_id}", 
                self.styles['Address']
            )
        
        # Dodaj NIP odbiorcy jeśli dostępny
        if self.client.tax_id:
            data[1][1] = Paragraph(
                f"{self.client.company_name or self.client.name}<br/>NIP: {self.client.tax_id}", 
                self.styles['Address']
            )
        
        # Dodaj adres wystawcy
        address_parts = []
        if self.user.address_line1:
            address_parts.append(self.user.address_line1)
        if self.user.address_line2:
            address_parts.append(self.user.address_line2)
        if self.user.postal_code or self.user.city:
            address_parts.append(f"{self.user.postal_code or ''} {self.user.city or ''}".strip())
        if self.user.country:
            address_parts.append(self.user.country)
        
        if address_parts:
            data.append([
                Paragraph("<br/>".join(address_parts), self.styles['Address']),
                ""
            ])
        
        # Dodaj adres odbiorcy
        client_address_parts = []
        if self.client.address_line1:
            client_address_parts.append(self.client.address_line1)
        if self.client.address_line2:
            client_address_parts.append(self.client.address_line2)
        if self.client.postal_code or self.client.city:
            client_address_parts.append(f"{self.client.postal_code or ''} {self.client.city or ''}".strip())
        if self.client.country:
            client_address_parts.append(self.client.country)
        
        if client_address_parts:
            if len(data) > 2:
                data[2][1] = Paragraph("<br/>".join(client_address_parts), self.styles['Address'])
            else:
                data.append([
                    "",
                    Paragraph("<br/>".join(client_address_parts), self.styles['Address'])
                ])
        
        # Kontakt wystawcy
        contact_parts = []
        if self.user.email:
            contact_parts.append(f"Email: {self.user.email}")
        if self.user.phone:
            contact_parts.append(f"Tel: {self.user.phone}")
        
        if contact_parts:
            if len(data) > 2:
                data.append([
                    Paragraph("<br/>".join(contact_parts), self.styles['Address']),
                    ""
                ])
            else:
                data.append([
                    Paragraph("<br/>".join(contact_parts), self.styles['Address']),
                    ""
                ])
        
        # Kontakt odbiorcy
        client_contact_parts = []
        if self.client.email:
            client_contact_parts.append(f"Email: {self.client.email}")
        if self.client.phone:
            client_contact_parts.append(f"Tel: {self.client.phone}")
        
        if client_contact_parts:
            if len(data) > 3:
                data[3][1] = Paragraph("<br/>".join(client_contact_parts), self.styles['Address'])
            else:
                data.append([
                    "",
                    Paragraph("<br/>".join(client_contact_parts), self.styles['Address'])
                ])
        
        # Utwórz tabelę
        table = Table(data, colWidths=[9*cm, 9*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10*mm))
    
    def _add_invoice_info(self, elements):
        """Dodaje informacje o fakturze."""
        # Tabela z informacjami o fakturze
        data = [
            [Paragraph("Data wystawienia:", self.styles['TableCell']), 
             Paragraph(self.invoice.issue_date.strftime("%d.%m.%Y"), self.styles['TableCellRight'])],
            
            [Paragraph("Termin płatności:", self.styles['TableCell']),
             Paragraph(self.invoice.due_date.strftime("%d.%m.%Y"), self.styles['TableCellRight'])],
            
            [Paragraph("Metoda płatności:", self.styles['TableCell']),
             Paragraph(self._get_payment_method_label(), self.styles['TableCellRight'])]
        ]
        
        # Dodaj datę płatności jeśli faktura została opłacona
        if self.invoice.payment_date:
            data.append([
                Paragraph("Data płatności:", self.styles['TableCell']),
                Paragraph(self.invoice.payment_date.strftime("%d.%m.%Y"), self.styles['TableCellRight'])
            ])
        
        # Utwórz tabelę
        table = Table(data, colWidths=[4*cm, 4*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        
        # Użyj tabeli z 2 kolumnami, aby wyrównać do prawej
        outer_data = [[table, ""]]
        outer_table = Table(outer_data, colWidths=[8*cm, 10*cm])
        outer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ]))
        
        elements.append(outer_table)
        elements.append(Spacer(1, 5*mm))
    
    def _get_payment_method_label(self):
        """Zwraca etykietę dla metody płatności."""
        payment_methods = {
            'bank_transfer': 'Przelew bankowy',
            'cash': 'Gotówka',
            'credit_card': 'Karta kredytowa',
            'paypal': 'PayPal',
            'stripe': 'Stripe',
            'other': 'Inna'
        }
        return payment_methods.get(self.invoice.payment_method, 'Przelew bankowy')
    
    def _add_items_table(self, elements):
        """Dodaje tabelę z pozycjami faktury."""
        # Nagłówki tabeli
        headers = [
            Paragraph("Lp.", self.styles['TableHeader']),
            Paragraph("Opis", self.styles['TableHeader']),
            Paragraph("Ilość", self.styles['TableHeader']),
            Paragraph("Jedn.", self.styles['TableHeader']),
            Paragraph("Cena jedn.", self.styles['TableHeader']),
            Paragraph("Wartość netto", self.styles['TableHeader'])
        ]
        
        # Dodaj nagłówek dla podatku tylko jeśli jest używany
        if self.invoice.tax_rate > 0:
            headers.extend([
                Paragraph("VAT %", self.styles['TableHeader']),
                Paragraph("Wartość brutto", self.styles['TableHeader'])
            ])
        
        data = [headers]
        
        # Dodaj pozycje faktury
        for i, item in enumerate(self.invoice.items, 1):
            row = [
                Paragraph(str(i), self.styles['TableCell']),
                Paragraph(item.description, self.styles['TableCell']),
                Paragraph(f"{float(item.quantity):.2f}".replace('.', ','), self.styles['TableCellRight']),
                Paragraph(item.unit, self.styles['TableCell']),
                Paragraph(f"{float(item.unit_price):.2f} zł".replace('.', ','), self.styles['TableCellRight']),
                Paragraph(f"{float(item.total):.2f} zł".replace('.', ','), self.styles['TableCellRight'])
            ]
            
            # Dodaj informacje o podatku tylko jeśli jest używany
            if self.invoice.tax_rate > 0:
                tax_rate = item.tax_rate if item.tax_rate is not None else self.invoice.tax_rate
                tax_amount = item.total * tax_rate / 100
                gross_amount = item.total + tax_amount
                
                row.extend([
                    Paragraph(f"{float(tax_rate):.0f}%", self.styles['TableCellRight']),
                    Paragraph(f"{float(gross_amount):.2f} zł".replace('.', ','), self.styles['TableCellRight'])
                ])
            
            data.append(row)
        
        # Szerokości kolumn
        if self.invoice.tax_rate > 0:
            col_widths = [1*cm, 8*cm, 1.5*cm, 1.5*cm, 2.5*cm, 2.5*cm, 1.5*cm, 2.5*cm]
        else:
            col_widths = [1*cm, 10*cm, 1.5*cm, 1.5*cm, 2.5*cm, 2.5*cm]
        
        # Utwórz tabelę
        table = Table(data, colWidths=col_widths)
        
        # Style tabeli
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Ilość
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),  # Ceny
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        elements.append(Spacer(1, 5*mm))
    
    def _add_summary(self, elements):
        """Dodaje podsumowanie faktury."""
        # Tabela z podsumowaniem
        data = [
            [Paragraph("Wartość netto:", self.styles['TableCell']), 
             Paragraph(f"{float(self.invoice.subtotal):.2f} zł".replace('.', ','), self.styles['TableCellRight'])]
        ]
        
        # Dodaj informacje o podatku tylko jeśli jest używany
        if self.invoice.tax_rate > 0:
            data.append([
                Paragraph(f"VAT ({float(self.invoice.tax_rate):.0f}%):", self.styles['TableCell']),
                Paragraph(f"{float(self.invoice.tax_amount):.2f} zł".replace('.', ','), self.styles['TableCellRight'])
            ])
        
        # Dodaj rabat tylko jeśli jest używany
        if self.invoice.discount > 0:
            data.append([
                Paragraph("Rabat:", self.styles['TableCell']),
                Paragraph(f"{float(self.invoice.discount):.2f} zł".replace('.', ','), self.styles['TableCellRight'])
            ])
        
        # Dodaj wartość brutto
        data.append([
            Paragraph("Razem do zapłaty:", self.styles['Total']),
            Paragraph(f"{float(self.invoice.total):.2f} zł".replace('.', ','), self.styles['Total'])
        ])
        
        # Utwórz tabelę
        table = Table(data, colWidths=[4*cm, 4*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
        ]))
        
        # Użyj tabeli z 2 kolumnami, aby wyrównać do prawej
        outer_data = [["", table]]
        outer_table = Table(outer_data, colWidths=[10*cm, 8*cm])
        outer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        
        elements.append(outer_table)
        elements.append(Spacer(1, 10*mm))
    
    def _add_notes(self, elements):
        """Dodaje notatki i warunki płatności."""
        # Dodaj warunki płatności jeśli są dostępne
        if self.invoice.terms:
            elements.append(Paragraph("Warunki płatności:", self.styles['TableHeader']))
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph(self.invoice.terms, self.styles['Notes']))
            elements.append(Spacer(1, 5*mm))
        
        # Dodaj notatki jeśli są dostępne
        if self.invoice.notes:
            elements.append(Paragraph("Uwagi:", self.styles['TableHeader']))
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph(self.invoice.notes, self.styles['Notes']))
    
    def _add_footer(self, elements):
        """Dodaje stopkę faktury."""
        elements.append(Spacer(1, 15*mm))
        
        # Dodaj linię podpisu
        data = [
            ["", ""],
            [Paragraph("____________________________", self.styles['TableCell']),
             Paragraph("____________________________", self.styles['TableCell'])],
            [Paragraph("Wystawił", self.styles['TableCell']),
             Paragraph("Odebrał", self.styles['TableCell'])]
        ]
        
        # Utwórz tabelę
        table = Table(data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (0, 2), 'CENTER'),
            ('ALIGN', (1, 1), (1, 2), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ]))
        
        elements.append(table)