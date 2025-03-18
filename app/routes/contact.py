# app/routes/contact.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.contact import Contact
from app.models.transaction import Transaction, TransactionType
from app.forms.contact_form import ContactForm

contact_bp = Blueprint('contact', __name__, url_prefix='/contacts')

@contact_bp.route('/')
@login_required
def index():
    contacts = Contact.query.filter_by(user_id=current_user.id).order_by(Contact.name).all()
    
    # Oblicz saldo dla każdego kontaktu
    for contact in contacts:
        contact.balance = contact.get_balance()
    
    return render_template('contact/index.html', contacts=contacts)

@contact_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = ContactForm()
    
    if form.validate_on_submit():
        contact = Contact(
            user_id=current_user.id,
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            notes=form.notes.data
        )
        
        db.session.add(contact)
        db.session.commit()
        
        flash('Kontakt został dodany pomyślnie.', 'success')
        return redirect(url_for('contact.index'))
    
    return render_template('contact/form.html', form=form, title='Nowy kontakt')

@contact_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    contact = Contact.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = ContactForm(obj=contact)
    
    if form.validate_on_submit():
        form.populate_obj(contact)
        db.session.commit()
        
        flash('Kontakt został zaktualizowany pomyślnie.', 'success')
        return redirect(url_for('contact.index'))
    
    return render_template('contact/form.html', form=form, title='Edytuj kontakt')

@contact_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    contact = Contact.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    # Sprawdź, czy istnieją transakcje
    if Transaction.query.filter_by(contact_id=id).first():
        flash('Nie można usunąć kontaktu, który ma powiązane transakcje.', 'danger')
        return redirect(url_for('contact.index'))
    
    db.session.delete(contact)
    db.session.commit()
    
    flash('Kontakt został usunięty pomyślnie.', 'success')
    return redirect(url_for('contact.index'))

@contact_bp.route('/<int:id>/view')
@login_required
def view(id):
    contact = Contact.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    transactions = Transaction.get_transaction_history(current_user.id, id)
    balance = contact.get_balance()
    
    return render_template(
        'contact/view.html', 
        contact=contact, 
        transactions=transactions, 
        balance=balance,
        TransactionType=TransactionType
    )