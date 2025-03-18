
# app/forms/transaction_form.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import datetime

class TransactionForm(FlaskForm):
    amount = DecimalField(
        'Kwota', 
        validators=[
            DataRequired(), 
            NumberRange(min=0.01, message='Kwota musi być większa od 0.')
        ],
        places=2
    )
    transaction_type = SelectField(
        'Typ transakcji', 
        validators=[DataRequired()], 
        coerce=int
    )
    description = TextAreaField('Opis', validators=[Optional()])
    date = DateField(
        'Data', 
        validators=[Optional()], 
        default=datetime.now
    )
    submit = SubmitField('Zapisz')