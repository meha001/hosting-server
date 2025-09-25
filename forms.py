from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, Regexp
from models import User

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={'placeholder': 'Username'})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={'placeholder': 'Password'})
    submit = SubmitField('Register')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('That username already exists.')

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={'placeholder': 'Username'})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={'placeholder': 'Password'})
    submit = SubmitField('Login')

class CreateApp(FlaskForm):
    NewApp = StringField(validators=[InputRequired(), Length(min=4, max=20), Regexp('^[a-zA-Z0-9_-]+$')], render_kw={'placeholder': 'New app'})
    submit = SubmitField('Create')