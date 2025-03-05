from flask import Blueprint, render_template, request, send_file, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Invoice, Client, InvoiceItem, InvoiceStatus
import pandas as pd
import io
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import calendar

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    """
    Strona główna raportu - pokazuje podsumowanie i formularze do generowania raportów
    """
    # Pobierz statystyki
    invoices_count = Invoice.query.filter_by(user_id=current_user.id).count()
    clients_count = Client.query.filter_by(user_id=current_user.id).count()
    
    # Pobierz sumę faktur według statusu
    total_paid = db.session.query(func.sum(Invoice.total))\
        .filter(Invoice.user_id == current_user.id)\
        .filter(Invoice.status == InvoiceStatus.PAID)\
        .scalar() or 0
    
    total_pending = db.session.query(func.sum(Invoice.total))\
        .filter(Invoice.user_id == current_user.id)\
        .filter(Invoice.status == InvoiceStatus.PENDING)\
        .scalar() or 0
    
    total_overdue = db.session.query(func.sum(Invoice.total))\
        .filter(Invoice.user_id == current_user.id)\
        .filter(Invoice.status == InvoiceStatus.OVERDUE)\
        .scalar() or 0
    
    # Pobierz lata dla formularza
    years = db.session.query(extract('year', Invoice.issue_date).distinct())\
        .filter(Invoice.user_id == current_user.id)\
        .order_by(extract('year', Invoice.issue_date).desc())\
        .all()
    years = [int(year[0]) for year in years]
    
    # Jeśli nie ma faktur, dodaj bieżący rok
    if not years:
        years = [datetime.now().year]
    
    # Pobierz listę klientów
    clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    
    return render_template('reports/index.html',
                          title='Raporty',
                          invoices_count=invoices_count,
                          clients_count=clients_count,
                          total_paid=float(total_paid),
                          total_pending=float(total_pending),
                          total_overdue=float(total_overdue),
                          years=years,
                          clients=clients)

@reports_bp.route('/monthly')
@login_required
def monthly():
    """
    Raport miesięczny - pokazuje podsumowanie faktur według miesięcy
    """
    year = request.args.get('year', datetime.now().year, type=int)
    
    # Pobierz dane dla każdego miesiąca
    monthly_data = []
    
    for month in range(1, 13):
        # Pobierz faktury dla danego miesiąca
        month_invoices = Invoice.query\
            .filter(Invoice.user_id == current_user.id)\
            .filter(extract('year', Invoice.issue_date) == year)\
            .filter(extract('month', Invoice.issue_date) == month)\
            .all()
        
        # Oblicz sumę faktur według statusu
        paid = sum(float(inv.total) for inv in month_invoices if inv.status == InvoiceStatus.PAID)
        pending = sum(float(inv.total) for inv in month_invoices if inv.status == InvoiceStatus.PENDING)
        overdue = sum(float(inv.total) for inv in month_invoices if inv.status == InvoiceStatus.OVERDUE)
        
        # Dodaj do listy
        monthly_data.append({
            'month': calendar.month_name[month],
            'month_num': month,
            'invoices_count': len(month_invoices),
            'paid': paid,
            'pending': pending,
            'overdue': overdue,
            'total': paid + pending + overdue
        })
    
    # Pobierz dostępne lata
    years = db.session.query(extract('year', Invoice.issue_date).distinct())\
        .filter(Invoice.user_id == current_user.id)\
        .order_by(extract('year', Invoice.issue_date).desc())\
        .all()
    years = [int(year[0]) for year in years]
    
    # Jeśli nie ma faktur, dodaj bieżący rok
    if not years:
        years = [datetime.now().year]
    
    return render_template('reports/monthly.html',
                          title=f'Raport miesięczny - {year}',
                          monthly_data=monthly_data,
                          selected_year=year,
                          years=years)

@reports_bp.route('/client')
@login_required
def client():
    """
    Raport klienta - pokazuje faktury dla wybranego klienta
    """
    client_id = request.args.get('client_id', type=int)
    
    if not client_id:
        flash('Wybierz klienta', 'warning')
        return redirect(url_for('reports.index'))
    
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    
    # Pobierz faktury dla klienta
    invoices = Invoice.query\
        .filter_by(client_id=client_id, user_id=current_user.id)\
        .order_by(Invoice.issue_date.desc())\
        .all()
    
    # Oblicz sumę faktur według statusu
    total_paid = sum(float(inv.total) for inv in invoices if inv.status == InvoiceStatus.PAID)
    total_pending = sum(float(inv.total) for inv in invoices if inv.status == InvoiceStatus.PENDING)
    total_overdue = sum(float(inv.total) for inv in invoices if inv.status == InvoiceStatus.OVERDUE)
    
    # Pobierz listę klientów
    clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    
    return render_template('reports/client.html',
                          title=f'Raport klienta - {client.name}',
                          client=client,
                          invoices=invoices,
                          total_paid=total_paid,
                          total_pending=total_pending,
                          total_overdue=total_overdue,
                          clients=clients)

@reports_bp.route('/export-monthly')
@login_required
def export_monthly():
    """
    Eksportuje raport miesięczny do pliku CSV
    """
    year = request.args.get('year', datetime.now().year, type=int)
    format = request.args.get('format', 'csv')
    
    # Pobierz dane dla każdego miesiąca
    data = []
    
    for month in range(1, 13):
        # Pobierz faktury dla danego miesiąca
        month_invoices = Invoice.query\
            .filter(Invoice.user_id == current_user.id)\
            .filter(extract('year', Invoice.issue_date) == year)\
            .filter(extract('month', Invoice.issue_date) == month)\
            .all()
        
        # Oblicz sumę faktur według statusu
        paid = sum(float(inv.total) for inv in month_invoices if inv.status == InvoiceStatus.PAID)
        pending = sum(float(inv.total) for inv in month_invoices if inv.status == InvoiceStatus.PENDING)
        overdue = sum(float(inv.total) for inv in month_invoices if inv.status == InvoiceStatus.OVERDUE)
        
        # Dodaj do listy
        data.append({
            'Miesiąc': calendar.month_name[month],
            'Liczba faktur': len(month_invoices),
            'Zapłacone': paid,
            'Oczekujące': pending,
            'Przeterminowane': overdue,
            'Suma': paid + pending + overdue
        })
    
    # Utwórz DataFrame
    df = pd.DataFrame(data)
    
    # Utwórz buffer
    buffer = io.BytesIO()
    
    # Eksportuj do wybranego formatu
    if format == 'excel':
        df.to_excel(buffer, index=False, engine='xlsxwriter')
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'raport_miesieczny_{year}.xlsx'
    else:  # csv
        df.to_csv(buffer, index=False)
        mimetype = 'text/csv'
        filename = f'raport_miesieczny_{year}.csv'
    
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

@reports_bp.route('/export-client')
@login_required
def export_client():
    """
    Eksportuje raport klienta do pliku CSV
    """
    client_id = request.args.get('client_id', type=int)
    format = request.args.get('format', 'csv')
    
    if not client_id:
        flash('Wybierz klienta', 'warning')
        return redirect(url_for('reports.index'))
    
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    
    # Pobierz faktury dla klienta
    invoices = Invoice.query\
        .filter_by(client_id=client_id, user_id=current_user.id)\
        .order_by(Invoice.issue_date.desc())\
        .all()
    
    # Przygotuj dane
    data = []
    
    for invoice in invoices:
        data.append({
            'Numer faktury': invoice.invoice_number,
            'Data wystawienia': invoice.issue_date.strftime('%Y-%m-%d'),
            'Termin płatności': invoice.due_date.strftime('%Y-%m-%d'),
            'Status': invoice.status,
            'Suma netto': float(invoice.subtotal),
            'VAT': float(invoice.tax_amount),
            'Suma brutto': float(invoice.total),
            'Metoda płatności': invoice.payment_method,
            'Data płatności': invoice.payment_date.strftime('%Y-%m-%d') if invoice.payment_date else ''
        })
    
    # Utwórz DataFrame
    df = pd.DataFrame(data)
    
    # Utwórz buffer
    buffer = io.BytesIO()
    
    # Eksportuj do wybranego formatu
    if format == 'excel':
        df.to_excel(buffer, index=False, engine='xlsxwriter')
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'raport_klienta_{client.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    else:  # csv
        df.to_csv(buffer, index=False)
        mimetype = 'text/csv'
        filename = f'raport_klienta_{client.name.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.csv'
    
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

@reports_bp.route('/export-all-invoices')
@login_required
def export_all_invoices():
    """
    Eksportuje wszystkie faktury do pliku CSV
    """
    format = request.args.get('format', 'csv')
    
    # Pobierz wszystkie faktury
    invoices = Invoice.query\
        .filter_by(user_id=current_user.id)\
        .order_by(Invoice.issue_date.desc())\
        .all()
    
    # Przygotuj dane
    data = []
    
    for invoice in invoices:
        client = Client.query.get(invoice.client_id)
        
        data.append({
            'Numer faktury': invoice.invoice_number,
            'Data wystawienia': invoice.issue_date.strftime('%Y-%m-%d'),
            'Termin płatności': invoice.due_date.strftime('%Y-%m-%d'),
            'Klient': client.name if client else 'Nieznany',
            'Status': invoice.status,
            'Suma netto': float(invoice.subtotal),
            'VAT': float(invoice.tax_amount),
            'Suma brutto': float(invoice.total),
            'Metoda płatności': invoice.payment_method,
            'Data płatności': invoice.payment_date.strftime('%Y-%m-%d') if invoice.payment_date else ''
        })
    
    # Utwórz DataFrame
    df = pd.DataFrame(data)
    
    # Utwórz buffer
    buffer = io.BytesIO()
    
    # Eksportuj do wybranego formatu
    if format == 'excel':
        df.to_excel(buffer, index=False, engine='xlsxwriter')
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        filename = f'wszystkie_faktury_{datetime.now().strftime("%Y%m%d")}.xlsx'
    else:  # csv
        df.to_csv(buffer, index=False)
        mimetype = 'text/csv'
        filename = f'wszystkie_faktury_{datetime.now().strftime("%Y%m%d")}.csv'
    
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )