from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, IntegerField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Optional
from app.models import Users, Services

def service_name_exists(form, field):
    """Validator to check if a service name already exists."""
    if Services.query.filter_by(service_type=field.data).first():
        raise ValidationError('A service with this name already exists.')

# A custom validator to check if a username is already taken.
def username_exists(form, field):
    if Users.query.filter_by(username=field.data).first():
        raise ValidationError('Username already exists. Please choose another.')

# A custom validator to check if an email is already registered.
def email_exists(form, field):
    if Users.query.filter_by(email=field.data).first():
        raise ValidationError('Email already registered. Please choose another.')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80), username_exists])
    email = StringField('Email', validators=[DataRequired(), Email(), email_exists])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    address = StringField('Address', validators=[Optional(), Length(max=200)])
    pin = StringField('PIN Code', validators=[Optional(), Length(max=10)])
    role = SelectField('Register as', choices=[('customer', 'Customer'), ('professional', 'Service Professional')], validators=[DataRequired()])
    
    # Professional-specific fields
    service_id = SelectField('Service', coerce=int, validators=[Optional()])
    description = TextAreaField('Description (Bio)', validators=[Optional(), Length(max=500)])
    experience = IntegerField('Years of Experience', validators=[Optional()])
    document = StringField('Verification Document URL', validators=[Optional(), Length(max=255)])
    
    submit = SubmitField('Register')

    # This method is needed to populate the 'service_id' choices dynamically
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_id.choices = [(s.id, s.service_type) for s in Services.query.order_by('service_type').all()]

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateServiceForm(FlaskForm):
    service_type = StringField('Service Name', validators=[DataRequired(), Length(max=80), service_name_exists])
    base_price = FloatField('Base Price', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Create Service')

class UpdateServiceForm(FlaskForm):
    service_type = StringField('Service Name', validators=[DataRequired(), Length(max=80)])
    base_price = FloatField('Base Price', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Update Service')

    def __init__(self, original_service_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_service_type = original_service_type

    def validate_service_type(self, service_type):
        """Check if the new name conflicts with an *other* service."""
        if service_type.data != self.original_service_type:
            if Services.query.filter_by(service_type=service_type.data).first():
                raise ValidationError('Another service with that name already exists.')

class ReviewForm(FlaskForm):
    rating = SelectField('Rating', coerce=int, choices=[(5, '5 - Excellent'), (4, '4 - Good'), (3, '3 - Average'), (2, '2 - Poor'), (1, '1 - Terrible')], validators=[DataRequired()])
    remarks = TextAreaField('Remarks', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Submit Review')


class ProfileForm(FlaskForm):
    # --- Field Definitions ---
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    address = StringField('Address', validators=[Optional(), Length(max=200)])
    pin = StringField('PIN Code', validators=[Optional(), Length(max=10)])
    description = TextAreaField('Description (Bio)', validators=[Optional(), Length(max=500)])
    experience = IntegerField('Years of Experience', validators=[Optional()])
    password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Update Profile')

    # --- Methods (Correctly Indented) ---
    def __init__(self, original_username, original_email, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = Users.query.filter_by(username=self.username.data).first()
            if user:
                raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = Users.query.filter_by(email=self.email.data).first()
            if user:
                raise ValidationError('That email is already registered. Please choose a different one.')

class BookingForm(FlaskForm):
    """Form for a customer to book a service."""
    proposed_price = FloatField('Your Proposed Price ($)', validators=[DataRequired()])
    service_id = IntegerField('Service ID', validators=[DataRequired()]) # This will be a hidden field
    submit = SubmitField('Send Request')

class UpdateRequestForm(FlaskForm):
    """Form for a customer to update their pending service request."""
    proposed_price = FloatField('Your Proposed Price ($)', validators=[DataRequired()])
    submit = SubmitField('Save Changes')

class HandleRequestForm(FlaskForm):
    """Form for a professional to accept or reject a request."""
    action = StringField('Action', validators=[DataRequired()])
    submit = SubmitField('Submit')