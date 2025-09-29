
# app/routes/transaction.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.contact import Contact
from app.models.transaction import Transaction, TransactionType
from app.forms.transaction_form import TransactionForm
from datetime import datetime

transaction_bp = Blueprint('transaction', __name__, url_prefix='/transactions')

@transaction_bp.route('/new/<int:contact_id>', methods=['GET', 'POST'])
@login_required
def new(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first_or_404()
    form = TransactionForm()
    
    # Ustaw opcje dla typów transakcji
    form.transaction_type.choices = [
        (TransactionType.LENT_TO.value, 'Pożyczyłem'),
        (TransactionType.BORROWED_FROM.value, 'Pożyczył mi'),
        (TransactionType.REPAID_TO.value, 'Oddałem'),
        (TransactionType.RECEIVED_FROM.value, 'Oddał mi')
    ]
    
    if form.validate_on_submit():
        transaction = Transaction(
            user_id=current_user.id,
            contact_id=contact.id,
            amount=form.amount.data,
            transaction_type=TransactionType(form.transaction_type.data),
            description=form.description.data,
            date=form.date.data or datetime.utcnow()
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transakcja została dodana pomyślnie.', 'success')
        return redirect(url_for('contact.view', id=contact.id))
    
    return render_template(
        'transaction/form.html',
        form=form,
        contact=contact,
        title='Nowa transakcja',
        TransactionType=TransactionType
    )

@transaction_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    transaction = Transaction.query.filter_by(
        id=id, 
        user_id=current_user.id
    ).first_or_404()
    
    form = TransactionForm(obj=transaction)
    
    # Ustaw opcje dla typów transakcji
    form.transaction_type.choices = [
        (TransactionType.LENT_TO.value, 'Pożyczyłem'),
        (TransactionType.BORROWED_FROM.value, 'Pożyczył mi'),
        (TransactionType.REPAID_TO.value, 'Oddałem'),
        (TransactionType.RECEIVED_FROM.value, 'Oddał mi')
    ]
    
    if form.validate_on_submit():
        form.populate_obj(transaction)
        transaction.transaction_type = TransactionType(form.transaction_type.data)
        db.session.commit()
        
        flash('Transakcja została zaktualizowana pomyślnie.', 'success')
        return redirect(url_for('contact.view', id=transaction.contact_id))
    
    return render_template(
        'transaction/form.html',
        form=form,
        contact=transaction.contact,
        title='Edytuj transakcję',
        TransactionType=TransactionType
    )

@transaction_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    transaction = Transaction.query.filter_by(
        id=id, 
        user_id=current_user.id
    ).first_or_404()
    
    contact_id = transaction.contact_id
    
    db.session.delete(transaction)
    db.session.commit()
    
    flash('Transakcja została usunięta pomyślnie.', 'success')
    return redirect(url_for('contact.view', id=contact_id))