from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Client
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, Email

client_bp = Blueprint('client', __name__, url_prefix='/client')

# Formularze
class ClientForm(FlaskForm):
    name = StringField('Nazwa', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    company_name = StringField('Nazwa firmy', validators=[Optional()])
    tax_id = StringField('NIP', validators=[Optional()])
    address_line1 = StringField('Adres - linia 1', validators=[Optional()])
    address_line2 = StringField('Adres - linia 2', validators=[Optional()])
    city = StringField('Miasto', validators=[Optional()])
    postal_code = StringField('Kod pocztowy', validators=[Optional()])
    country = StringField('Kraj', validators=[Optional()])
    phone = StringField('Telefon', validators=[Optional()])
    notes = TextAreaField('Notatki', validators=[Optional()])
    is_active = BooleanField('Aktywny', default=True)
    submit = SubmitField('Zapisz')

# Trasy
@client_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Dodaje nowego klienta."""
    form = ClientForm()
    
    if form.validate_on_submit():
        client = Client(
            user_id=current_user.id,
            name=form.name.data,
            email=form.email.data,
            company_name=form.company_name.data,
            tax_id=form.tax_id.data,
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data,
            city=form.city.data,
            postal_code=form.postal_code.data,
            country=form.country.data,
            phone=form.phone.data,
            notes=form.notes.data,
            is_active=form.is_active.data
        )
        
        db.session.add(client)
        db.session.commit()
        
        flash('Klient został dodany pomyślnie', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Błąd w polu {getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('dashboard.clients'))

@client_bp.route('/<int:client_id>', methods=['GET'])
@login_required
def get(client_id):
    """Pobiera dane klienta."""
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    
    return jsonify(client.to_dict())

@client_bp.route('/<int:client_id>/update', methods=['POST'])
@login_required
def update(client_id):
    """Aktualizuje dane klienta."""
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    form = ClientForm()
    
    if form.validate_on_submit():
        client.name = form.name.data
        client.email = form.email.data
        client.company_name = form.company_name.data
        client.tax_id = form.tax_id.data
        client.address_line1 = form.address_line1.data
        client.address_line2 = form.address_line2.data
        client.city = form.city.data
        client.postal_code = form.postal_code.data
        client.country = form.country.data
        client.phone = form.phone.data
        client.notes = form.notes.data
        client.is_active = form.is_active.data
        
        db.session.commit()
        
        flash('Klient został zaktualizowany pomyślnie', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Błąd w polu {getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('dashboard.clients'))

@client_bp.route('/<int:client_id>/delete', methods=['POST'])
@login_required
def delete(client_id):
    """Usuwa klienta."""
    client = Client.query.filter_by(id=client_id, user_id=current_user.id).first_or_404()
    
    # Sprawdź, czy klient ma faktury
    if client.invoices.count() > 0:
        flash('Nie można usunąć klienta, który ma przypisane faktury', 'danger')
        return redirect(url_for('dashboard.clients'))
    
    db.session.delete(client)
    db.session.commit()
    
    flash('Klient został usunięty pomyślnie', 'success')
    return redirect(url_for('dashboard.clients'))