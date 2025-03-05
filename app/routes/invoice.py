from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, abort, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Invoice, InvoiceItem, Client, InvoiceStatus, PaymentMethod
from app.services.invoice_generator import InvoicePDFGenerator
from app.services.invoice_numbering import InvoiceNumberGenerator
from app.services.payment_integration import PaymentService
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, FieldList, FormField, HiddenField, DateField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import datetime, timedelta
import json

invoice_bp = Blueprint('invoice', __name__, url_prefix='/invoice')

# Formularze
class InvoiceItemForm(FlaskForm):
    id = HiddenField('ID')
    description = StringField('Opis', validators=[DataRequired()])
    quantity = DecimalField('Ilość', default=1, validators=[DataRequired(), NumberRange(min=0.01)])
    unit = StringField('Jednostka', default='szt.')
    unit_price = DecimalField('Cena jednostkowa', validators=[DataRequired(), NumberRange(min=0)])
    tax_rate = DecimalField('Stawka VAT (%)', default=23)

class InvoiceForm(FlaskForm):
    invoice_number = StringField('Numer faktury', validators=[DataRequired()])
    client_id = SelectField('Klient', coerce=int, validators=[DataRequired()])
    issue_date = DateField('Data wystawienia', format='%Y-%m-%d', validators=[DataRequired()])
    due_date = DateField('Termin płatności', format='%Y-%m-%d', validators=[DataRequired()])
    payment_method = SelectField('Metoda płatności', choices=[
        (PaymentMethod.BANK_TRANSFER, 'Przelew bankowy'),
        (PaymentMethod.CASH, 'Gotówka'),
        (PaymentMethod.CREDIT_CARD, 'Karta kredytowa'),
        (PaymentMethod.PAYPAL, 'PayPal'),
        (PaymentMethod.STRIPE, 'Stripe'),
        (PaymentMethod.OTHER, 'Inna')
    ], validators=[DataRequired()])
    status = SelectField('Status', choices=[
        (InvoiceStatus.DRAFT, 'Szkic'),
        (InvoiceStatus.PENDING, 'Oczekująca'),
        (InvoiceStatus.PAID, 'Opłacona'),
        (InvoiceStatus.OVERDUE, 'Przeterminowana'),
        (InvoiceStatus.CANCELED, 'Anulowana')
    ], validators=[DataRequired()])
    tax_rate = DecimalField('Stawka VAT (%)', default=23)
    discount = DecimalField('Rabat', default=0)
    notes = TextAreaField('Uwagi')
    terms = TextAreaField('Warunki płatności')
    items = FieldList(FormField(InvoiceItemForm), min_entries=1)

# Trasy
@invoice_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    # Tworzymy pusty formularz
    form = InvoiceForm()
    
    # Wypełnienie listy klientów
    form.client_id.choices = [(c.id, c.name) for c in 
                              Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()]
    
    # Domyślne wartości dla dat w przypadku GETa
    if request.method == 'GET':
        today = datetime.utcnow().date()
        form.issue_date.data = today
        form.due_date.data = today + timedelta(days=14)
        form.invoice_number.data = InvoiceNumberGenerator.get_next_number(current_user.id)
    
    # Jeśli formularz jest wysyłany metodą POST
    if request.method == 'POST':
        # Logowanie formularza - DEBUG
        print("Form Data:", request.form)
        
        try:
            # Zbieramy dane formularza
            invoice_data = {
                'invoice_number': request.form.get('invoice_number'),
                'client_id': request.form.get('client_id'),
                'issue_date': datetime.strptime(request.form.get('issue_date'), '%Y-%m-%d').date() if request.form.get('issue_date') else None,
                'due_date': datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date() if request.form.get('due_date') else None,
                'payment_method': request.form.get('payment_method'),
                'status': request.form.get('status'),
                'tax_rate': float(request.form.get('tax_rate', 0)),
                'discount': float(request.form.get('discount', 0)),
                'notes': request.form.get('notes', ''),
                'terms': request.form.get('terms', '')
            }
            
            # Walidacja podstawowych pól
            errors = {}
            if not invoice_data['invoice_number']:
                errors['invoice_number'] = 'To pole jest wymagane'
            if not invoice_data['client_id']:
                errors['client_id'] = 'To pole jest wymagane'
            if not invoice_data['issue_date']:
                errors['issue_date'] = 'To pole jest wymagane'
            if not invoice_data['due_date']:
                errors['due_date'] = 'To pole jest wymagane'
            if not invoice_data['payment_method']:
                errors['payment_method'] = 'To pole jest wymagane'
            if not invoice_data['status']:
                errors['status'] = 'To pole jest wymagane'
                
            # Szukamy kluczy, które wskazują na pozycje faktury
            invoice_items = []
            item_keys = set()
            
            # Znajdujemy wszystkie klucze opisów pozycji faktury
            for key in request.form:
                if key.startswith('items-') and key.endswith('-description'):
                    item_index = key.split('-')[1]
                    item_keys.add(item_index)
            
            print("Znalezione indeksy pozycji:", item_keys)
            
            # Zbieramy dane dla każdej pozycji
            for item_index in item_keys:
                try:
                    description = request.form.get(f'items-{item_index}-description', '')
                    if not description:  # Pomijamy puste pozycje
                        continue
                        
                    quantity_str = request.form.get(f'items-{item_index}-quantity', '1')
                    quantity = float(quantity_str) if quantity_str else 1
                    
                    unit = request.form.get(f'items-{item_index}-unit', 'szt.')
                    
                    unit_price_str = request.form.get(f'items-{item_index}-unit_price', '0')
                    unit_price = float(unit_price_str) if unit_price_str else 0
                    
                    tax_rate_str = request.form.get(f'items-{item_index}-tax_rate', '')
                    tax_rate = float(tax_rate_str) if tax_rate_str else invoice_data['tax_rate']
                    
                    item_data = {
                        'description': description,
                        'quantity': quantity,
                        'unit': unit,
                        'unit_price': unit_price,
                        'tax_rate': tax_rate
                    }
                    
                    # Walidacja pozycji
                    if not description:
                        errors[f'items-{item_index}-description'] = 'Opis jest wymagany'
                    if quantity <= 0:
                        errors[f'items-{item_index}-quantity'] = 'Ilość musi być większa od zera'
                    if unit_price < 0:
                        errors[f'items-{item_index}-unit_price'] = 'Cena nie może być ujemna'
                    
                    invoice_items.append(item_data)
                    
                except (ValueError, TypeError) as e:
                    errors[f'items-{item_index}'] = f'Błąd w pozycji: {str(e)}'
            
            print(f"Znaleziono {len(invoice_items)} pozycji faktury")
            
            # Sprawdź, czy jest co najmniej jedna pozycja
            if len(invoice_items) == 0:
                errors['items'] = 'Faktura musi zawierać co najmniej jedną pozycję'
            
            # Jeśli są błędy, wyświetl je i wróć do formularza
            if errors:
                for field, error in errors.items():
                    flash(f'Błąd w polu {field}: {error}', 'danger')
                return render_template('invoice/create.html', title='Utwórz fakturę', form=form)
            
            # Jeśli wszystko OK, twórz fakturę
            invoice = Invoice(
                user_id=current_user.id,
                client_id=int(invoice_data['client_id']),
                invoice_number=invoice_data['invoice_number'],
                issue_date=invoice_data['issue_date'],
                due_date=invoice_data['due_date'],
                payment_method=invoice_data['payment_method'],
                status=invoice_data['status'],
                tax_rate=invoice_data['tax_rate'],
                discount=invoice_data['discount'],
                notes=invoice_data['notes'],
                terms=invoice_data['terms']
            )
            
            db.session.add(invoice)
            db.session.flush()  # Aby uzyskać ID faktury
            
            # Dodaj pozycje faktury
            for item_data in invoice_items:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data['description'],
                    quantity=item_data['quantity'],
                    unit=item_data['unit'],
                    unit_price=item_data['unit_price'],
                    tax_rate=item_data['tax_rate'] if item_data['tax_rate'] != invoice_data['tax_rate'] else None
                )
                db.session.add(item)
            
            # Oblicz wartości faktury
            db.session.flush()
            invoice.calculate_totals()
            
            db.session.commit()
            flash('Faktura została utworzona pomyślnie', 'success')
            return redirect(url_for('invoice.view', invoice_id=invoice.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Wystąpił błąd podczas zapisywania faktury: {str(e)}', 'danger')
            import traceback
            print(traceback.format_exc())
    
    return render_template('invoice/create.html', title='Utwórz fakturę', form=form)


@invoice_bp.route('/<int:invoice_id>')
@login_required
def view(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    client = Client.query.get_or_404(invoice.client_id)
    
    # Sprawdź, czy faktura jest przeterminowana i zaktualizuj status
    if invoice.is_overdue() and invoice.status != InvoiceStatus.PAID:
        invoice.status = InvoiceStatus.OVERDUE
        db.session.commit()
    
    return render_template('invoice/view.html', title=f'Faktura {invoice.invoice_number}', 
                          invoice=invoice, client=client)

@invoice_bp.route('/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    
    # Nie pozwól na edycję faktury, która jest już opłacona
    if invoice.status == InvoiceStatus.PAID:
        flash('Nie można edytować faktury, która została już opłacona', 'warning')
        return redirect(url_for('invoice.view', invoice_id=invoice.id))
    
    form = InvoiceForm(obj=invoice)
    
    # Wypełnienie listy klientów
    form.client_id.choices = [(c.id, c.name) for c in 
                              Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()]
    
    if request.method == 'GET':
        # Wypełnij pozycje faktury
        form.items.pop_entry()  # Usuń domyślne puste pole
        for item in invoice.items:
            form.items.append_entry({
                'id': item.id,
                'description': item.description,
                'quantity': item.quantity,
                'unit': item.unit,
                'unit_price': item.unit_price,
                'tax_rate': item.tax_rate or invoice.tax_rate
            })
    
    if form.validate_on_submit():
        # Aktualizuj fakturę
        invoice.client_id = form.client_id.data
        invoice.invoice_number = form.invoice_number.data
        invoice.issue_date = form.issue_date.data
        invoice.due_date = form.due_date.data
        invoice.payment_method = form.payment_method.data
        invoice.status = form.status.data
        invoice.tax_rate = form.tax_rate.data
        invoice.discount = form.discount.data
        invoice.notes = form.notes.data
        invoice.terms = form.terms.data
        
        # Usuń istniejące pozycje i dodaj nowe
        InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
        
        # Zbierz pozycje faktury z formularza
        item_count = 0
        while True:
            description_key = f'items-{item_count}-description'
            if description_key not in request.form:
                break
                
            try:
                description = request.form[description_key]
                quantity = float(request.form[f'items-{item_count}-quantity'])
                unit = request.form[f'items-{item_count}-unit']
                unit_price = float(request.form[f'items-{item_count}-unit_price'])
                tax_rate = float(request.form[f'items-{item_count}-tax_rate']) if request.form[f'items-{item_count}-tax_rate'] else None
                
                # Dodaj pozycję faktury
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=description,
                    quantity=quantity,
                    unit=unit,
                    unit_price=unit_price,
                    tax_rate=tax_rate
                )
                db.session.add(item)
                
            except (KeyError, ValueError) as e:
                flash(f'Błąd przetwarzania pozycji faktury {item_count+1}: {str(e)}', 'danger')
                return render_template('invoice/edit.html', title=f'Edytuj fakturę {invoice.invoice_number}', 
                                    form=form, invoice=invoice)
            
            item_count += 1
        
        if item_count == 0:
            flash('Faktura musi zawierać co najmniej jedną pozycję', 'danger')
            return render_template('invoice/edit.html', title=f'Edytuj fakturę {invoice.invoice_number}', 
                                form=form, invoice=invoice)
        
        # Oblicz wartości faktury
        db.session.flush()
        invoice.calculate_totals()
        
        db.session.commit()
        flash('Faktura została zaktualizowana pomyślnie', 'success')
        return redirect(url_for('invoice.view', invoice_id=invoice.id))
    elif request.method == 'POST':
        # Wyświetl błędy walidacji formularza
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Błąd w polu {field}: {error}', 'danger')
    
    return render_template('invoice/edit.html', title=f'Edytuj fakturę {invoice.invoice_number}', 
                          form=form, invoice=invoice)

@invoice_bp.route('/<int:invoice_id>/download')
@login_required
def download(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    client = Client.query.get_or_404(invoice.client_id)
    
    # Generowanie PDF
    pdf_generator = InvoicePDFGenerator(invoice, current_user, client)
    pdf_buffer = pdf_generator.generate()
    
    # Przygotowanie nazwy pliku
    filename = f"Faktura_{invoice.invoice_number.replace('/', '_')}.pdf"
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

@invoice_bp.route('/<int:invoice_id>/mark-as-paid', methods=['POST'])
@login_required
def mark_as_paid(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    
    # Sprawdź czy faktura nie jest już opłacona
    if invoice.status == InvoiceStatus.PAID:
        flash('Faktura jest już oznaczona jako opłacona', 'info')
        return redirect(url_for('invoice.view', invoice_id=invoice.id))
    
    # Pobierz datę płatności (jeśli podana)
    payment_date = request.form.get('payment_date')
    if payment_date:
        try:
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        except ValueError:
            payment_date = datetime.utcnow().date()
    else:
        payment_date = datetime.utcnow().date()
    
    payment_id = request.form.get('payment_id', '')
    
    # Oznacz fakturę jako opłaconą
    invoice.mark_as_paid(payment_date, payment_id)
    db.session.commit()
    
    flash('Faktura została oznaczona jako opłacona', 'success')
    return redirect(url_for('invoice.view', invoice_id=invoice.id))

@invoice_bp.route('/<int:invoice_id>/delete', methods=['POST'])
@login_required
def delete(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    
    # Nie pozwól na usunięcie faktury, która jest już opłacona
    if invoice.status == InvoiceStatus.PAID:
        flash('Nie można usunąć faktury, która została już opłacona', 'warning')
        return redirect(url_for('invoice.view', invoice_id=invoice.id))
    
    # Usuń fakturę
    db.session.delete(invoice)
    db.session.commit()
    
    flash('Faktura została usunięta pomyślnie', 'success')
    return redirect(url_for('dashboard.invoices'))

@invoice_bp.route('/<int:invoice_id>/create-payment-link', methods=['POST'])
@login_required
def create_payment_link(invoice_id):
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    
    # Sprawdź czy faktura nie jest już opłacona
    if invoice.status == InvoiceStatus.PAID:
        flash('Faktura jest już opłacona', 'info')
        return redirect(url_for('invoice.view', invoice_id=invoice.id))
    
    # Wybierz metodę płatności
    payment_method = request.form.get('payment_method', 'stripe')
    
    try:
        if payment_method == 'stripe':
            payment_info = PaymentService.create_stripe_payment_link(invoice)
        elif payment_method == 'paypal':
            payment_info = PaymentService.create_paypal_payment(invoice)
        else:
            flash('Nieobsługiwana metoda płatności', 'danger')
            return redirect(url_for('invoice.view', invoice_id=invoice.id))
        
        if not payment_info:
            flash('Nie udało się utworzyć linku do płatności', 'danger')
            return redirect(url_for('invoice.view', invoice_id=invoice.id))
        
        # Zapisz ID sesji/płatności do późniejszej weryfikacji
        invoice.payment_id = payment_info.get('session_id') or payment_info.get('payment_id')
        invoice.status = InvoiceStatus.PENDING
        db.session.commit()
        
        return redirect(payment_info['payment_url'])
        
    except Exception as e:
        flash(f'Wystąpił błąd podczas tworzenia linku do płatności: {str(e)}', 'danger')
        return redirect(url_for('invoice.view', invoice_id=invoice.id))

@invoice_bp.route('/payment-success')
@login_required
def payment_success():
    invoice_id = request.args.get('invoice_id')
    session_id = request.args.get('session_id')
    
    if not invoice_id:
        flash('Brak identyfikatora faktury', 'danger')
        return redirect(url_for('dashboard.invoices'))
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    
    # Sprawdź status płatności w Stripe (jeśli podano session_id)
    if session_id:
        try:
            if PaymentService.verify_stripe_payment(session_id):
                invoice.mark_as_paid(datetime.utcnow().date(), session_id)
                db.session.commit()
                flash('Płatność została zrealizowana pomyślnie!', 'success')
            else:
                flash('Weryfikacja płatności nie powiodła się', 'warning')
        except Exception as e:
            flash(f'Wystąpił błąd podczas weryfikacji płatności: {str(e)}', 'danger')
    else:
        # Jeśli brak session_id, po prostu oznacz jako opłacone (zaufaj odpowiedzi)
        invoice.mark_as_paid(datetime.utcnow().date())
        db.session.commit()
        flash('Płatność została zrealizowana pomyślnie!', 'success')
    
    return redirect(url_for('invoice.view', invoice_id=invoice.id))

@invoice_bp.route('/payment-cancel')
@login_required
def payment_cancel():
    invoice_id = request.args.get('invoice_id')
    
    if not invoice_id:
        flash('Brak identyfikatora faktury', 'danger')
        return redirect(url_for('dashboard.invoices'))
    
    flash('Płatność została anulowana', 'warning')
    return redirect(url_for('invoice.view', invoice_id=invoice_id))

@invoice_bp.route('/paypal-success')
@login_required
def paypal_success():
    invoice_id = request.args.get('invoice_id')
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    
    if not invoice_id or not payment_id or not payer_id:
        flash('Brak wymaganych parametrów', 'danger')
        return redirect(url_for('dashboard.invoices'))
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user.id).first_or_404()
    
    # Wykonaj płatność w PayPal
    try:
        import paypalrestsdk
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            invoice.mark_as_paid(datetime.utcnow().date(), payment_id)
            db.session.commit()
            flash('Płatność PayPal została zrealizowana pomyślnie!', 'success')
        else:
            flash('Wykonanie płatności PayPal nie powiodło się', 'danger')
    except Exception as e:
        flash(f'Wystąpił błąd podczas realizacji płatności PayPal: {str(e)}', 'danger')
    
    return redirect(url_for('invoice.view', invoice_id=invoice.id))

@invoice_bp.route('/paypal-cancel')
@login_required
def paypal_cancel():
    invoice_id = request.args.get('invoice_id')
    
    if not invoice_id:
        flash('Brak identyfikatora faktury', 'danger')
        return redirect(url_for('dashboard.invoices'))
    
    flash('Płatność PayPal została anulowana', 'warning')
    return redirect(url_for('invoice.view', invoice_id=invoice_id))

@invoice_bp.route('/calculate-totals', methods=['POST'])
@login_required
def calculate_totals():
    """
    API endpoint dla obliczania wartości faktury na podstawie podanych danych.
    Używane przez JavaScript w formularzu faktury.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Brak danych'}), 400
        
        items = data.get('items', [])
        tax_rate = float(data.get('tax_rate', 0))
        discount = float(data.get('discount', 0))
        
        # Oblicz sumę wartości pozycji
        subtotal = 0
        for item in items:
            quantity = float(item.get('quantity', 0))
            price = float(item.get('unit_price', 0))
            item_total = quantity * price
            subtotal += item_total
        
        # Oblicz podatek
        tax_amount = subtotal * tax_rate / 100
        
        # Oblicz wartość końcową
        total = subtotal + tax_amount - discount
        
        return jsonify({
            'subtotal': round(subtotal, 2),
            'tax_amount': round(tax_amount, 2),
            'total': round(total, 2)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400