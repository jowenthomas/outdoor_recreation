from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class SubmitForm(FlaskForm):
    zipCode = StringField('Zip Code', validators=[DataRequired()])
    submit = SubmitField('View Content')