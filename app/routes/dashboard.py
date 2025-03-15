from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Invoice, Client, InvoiceStatus
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from sqlalchemy import func
import calendar

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """
    Dashboard główny - pokazuje podsumowanie faktur i statystyki.
    """
    # Statystyki faktur
    total_invoices = Invoice.query.filter_by(user_id=current_user.id).count()
    pending_invoices = Invoice.query.filter_by(user_id=current_user.id, status=InvoiceStatus.PENDING).count()
    paid_invoices = Invoice.query.filter_by(user_id=current_user.id, status=InvoiceStatus.PAID).count()
    overdue_invoices = Invoice.query.filter_by(user_id=current_user.id, status=InvoiceStatus.OVERDUE).count()
    
    # Najnowsze faktury
    recent_invoices = Invoice.query.filter_by(user_id=current_user.id)\
        .order_by(Invoice.created_at.desc())\
        .limit(5).all()
    
    # Faktury, których termin płatności zbliża się (w ciągu 7 dni)
    upcoming_due_date = datetime.utcnow().date() + timedelta(days=7)
    upcoming_invoices = Invoice.query.filter_by(user_id=current_user.id)\
        .filter(Invoice.status == InvoiceStatus.PENDING)\
        .filter(Invoice.due_date <= upcoming_due_date)\
        .order_by(Invoice.due_date.asc())\
        .limit(5).all()
    
 # Przychód miesięczny (ostatnie 6 miesięcy)
    monthly_revenue = []
    today = datetime.today()

    for i in range(5, -1, -1):
        month = (today.month - i - 1) % 12 + 1
        year = today.year + ((today.month - i - 1) // 12)

        first_day = datetime(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, days_in_month, 23, 59, 59)

        total = db.session.query(func.sum(Invoice.total))\
            .filter(
                Invoice.user_id == current_user.id,
                Invoice.status == InvoiceStatus.PAID,
                Invoice.payment_date >= first_day,
                Invoice.payment_date <= last_day
            ).scalar() or 0

        monthly_revenue.append({
            'month': calendar.month_name[month],
            'total': float(total)
        })


    # Pobierz najlepszych klientów (wg. wartości faktur)
    top_clients = db.session.query(
        Client.name,
        func.sum(Invoice.total).label('total_value')
    ).join(Invoice, Invoice.client_id == Client.id)\
     .filter(Client.user_id == current_user.id)\
     .group_by(Client.id)\
     .order_by(func.sum(Invoice.total).desc())\
     .limit(5).all()

    # Podsumowanie płatności
    total_paid = db.session.query(func.sum(Invoice.total))\
        .filter_by(user_id=current_user.id, status=InvoiceStatus.PAID)\
        .scalar() or 0

    total_pending = db.session.query(func.sum(Invoice.total))\
        .filter(
            Invoice.user_id == current_user.id,
            Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.OVERDUE])
        ).scalar() or 0

    
    # Pobierz najlepszych klientów (wg. wartości faktur)
    top_clients = db.session.query(
            Client.name,
            func.sum(Invoice.total).label('total_value')
        )\
        .join(Invoice, Invoice.client_id == Client.id)\
        .filter(Client.user_id == current_user.id)\
        .group_by(Client.id)\
        .order_by(func.sum(Invoice.total).desc())\
        .limit(5).all()
    
    # Podsumowanie płatności
    total_paid = db.session.query(func.sum(Invoice.total))\
        .filter(Invoice.user_id == current_user.id)\
        .filter(Invoice.status == InvoiceStatus.PAID)\
        .scalar() or 0
    
    total_pending = db.session.query(func.sum(Invoice.total))\
        .filter(Invoice.user_id == current_user.id)\
        .filter(Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.OVERDUE]))\
        .scalar() or 0


    return render_template('dashboard/index.html',
                           title='Dashboard',
                           total_invoices=total_invoices,
                           pending_invoices=pending_invoices,
                           paid_invoices=paid_invoices,
                           overdue_invoices=overdue_invoices,
                           recent_invoices=recent_invoices,
                           upcoming_invoices=upcoming_invoices,
                           monthly_revenue=monthly_revenue[-6:],  # ostatnie 6 miesięcy
                           top_clients=top_clients,
                           total_paid=float(total_paid),
                           total_pending=float(total_pending))


@dashboard_bp.route('/invoices')
@login_required
def invoices():
    """
    Lista wszystkich faktur.
    """
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    # Buduj zapytanie
    query = Invoice.query.filter_by(user_id=current_user.id)
    
    # Filtruj według statusu
    if status != 'all' and status in InvoiceStatus.all():
        query = query.filter_by(status=status)
    
    # Sortuj wg daty wystawienia (najnowsze najpierw)
    query = query.order_by(Invoice.issue_date.desc())
    
    # Paginacja
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    invoices = pagination.items
    
    # Przygotuj dane dla listy rozwijalnej statusów
    status_choices = [('all', 'Wszystkie faktury')] + [(s, s.capitalize()) for s in InvoiceStatus.all()]
    
    return render_template('dashboard/invoices.html',
                          title='Faktury',
                          invoices=invoices,
                          pagination=pagination,
                          status=status,
                          status_choices=status_choices)

@dashboard_bp.route('/clients')
@login_required
def clients():
    """
    Lista klientów.
    """
    page = request.args.get('page', 1, type=int)
    
    # Buduj zapytanie
    query = Client.query.filter_by(user_id=current_user.id)
    
    # Sortuj wg nazwy klienta
    query = query.order_by(Client.name)
    
    # Paginacja
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    clients = pagination.items
    
    return render_template('dashboard/clients.html',
                          title='Klienci',
                          clients=clients,
                          pagination=pagination)