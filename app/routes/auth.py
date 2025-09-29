from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Formularze
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    remember_me = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField(
        'Powtórz hasło', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('Imię', validators=[DataRequired()])
    last_name = StringField('Nazwisko', validators=[DataRequired()])
    submit = SubmitField('Zarejestruj')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()
        if user is not None:
            raise ValidationError('Ten adres email jest już zarejestrowany.')

class ProfileForm(FlaskForm):
    first_name = StringField('Imię', validators=[DataRequired()])
    last_name = StringField('Nazwisko', validators=[DataRequired()])
    submit = SubmitField('Zapisz zmiany')

class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Aktualne hasło', validators=[DataRequired()])
    new_password = PasswordField('Nowe hasło', validators=[DataRequired(), Length(min=8)])
    new_password2 = PasswordField(
        'Powtórz nowe hasło', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Zmień hasło')

# Trasy
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash('Nieprawidłowy email lub hasło', 'danger')
            return redirect(url_for('auth.login'))
        
        # Aktualizacja ostatniego logowania
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard.index')
        
        flash('Zalogowano pomyślnie!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Logowanie', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Wylogowano pomyślnie', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data.lower(),
            password=form.password.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            confirmed=True  # Dla uproszczenia, w produkcji powinien być proces weryfikacji email
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Gratulacje, rejestracja zakończona pomyślnie!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Rejestracja', form=form)

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        
        db.session.commit()
        flash('Profil zaktualizowany pomyślnie', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', title='Mój profil', form=form)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Aktualne hasło jest nieprawidłowe', 'danger')
            return redirect(url_for('auth.change_password'))
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Hasło zostało zmienione pomyślnie', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/change_password.html', title='Zmiana hasła', form=form)