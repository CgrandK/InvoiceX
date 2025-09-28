from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Contact
from datetime import datetime, timedelta


dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """
    Dashboard główny - pokazuje podsumowanie faktur i statystyki.
    """


    # Dodaj dane dla widżetu pożyczek
    contacts_with_debt = Contact.query.filter_by(user_id=current_user.id).all()
    for contact in contacts_with_debt:
        contact.balance = contact.get_balance()
    
    # Filtruj kontakty z niezerowym saldem
    contacts_with_debt = [c for c in contacts_with_debt if c.balance != 0]
    
    # Sortuj kontakty: najpierw te, którym pożyczyliśmy (saldo dodatnie)
    contacts_with_debt.sort(key=lambda c: c.balance, reverse=True)
    
    # Oblicz sumy
    total_to_receive = sum(c.balance for c in contacts_with_debt if c.balance > 0)
    total_to_pay = sum(abs(c.balance) for c in contacts_with_debt if c.balance < 0)

    return render_template(
        'dashboard/index.html',
        title='Dashboard',
        contacts_with_debt=contacts_with_debt[:5],
        total_to_receive=float(total_to_receive),
        total_to_pay=float(total_to_pay),
    )
