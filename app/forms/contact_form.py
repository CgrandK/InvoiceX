# app/forms/contact_form.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length

class ContactForm(FlaskForm):
    name = StringField('Nazwa', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Telefon', validators=[Optional(), Length(max=20)])
    notes = TextAreaField('Notatki', validators=[Optional()])
    submit = SubmitField('Zapisz')