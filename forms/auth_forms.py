"""
Authentication forms for JobSearchAI application.
Contains WTForms classes for login and registration with validation.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp
from models.user import User


class LoginForm(FlaskForm):
    """
    Form for user login with username or email.
    
    Fields:
        username_or_email: Can accept either username or email address
        password: User's password
        remember_me: Checkbox for persistent login
        submit: Submit button
    """
    
    username_or_email = StringField(
        'Username or Email',
        validators=[
            DataRequired(message='Username or email is required.'),
            Length(min=3, max=120, message='Username or email must be between 3 and 120 characters.')
        ],
        render_kw={'placeholder': 'Enter username or email', 'class': 'form-control'}
    )
    
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.')
        ],
        render_kw={'placeholder': 'Enter password', 'class': 'form-control'}
    )
    
    remember_me = BooleanField(
        'Remember Me',
        render_kw={'class': 'form-check-input'}
    )
    
    submit = SubmitField(
        'Sign In',
        render_kw={'class': 'btn btn-primary w-100'}
    )
    
    def validate_username_or_email(self, field):
        """
        Custom validator to check if user exists with given username or email.
        
        Args:
            field: The username_or_email field
            
        Raises:
            ValidationError: If no user found with given credentials
        """
        user = User.find_by_username_or_email(field.data)
        if not user:
            raise ValidationError('No account found with this username or email.')
        if not user.is_active:
            raise ValidationError('This account has been deactivated.')


class RegistrationForm(FlaskForm):
    """
    Form for user registration.
    
    Fields:
        username: Unique username (3-20 characters, alphanumeric + underscore)
        email: Unique email address
        password: Password (minimum 8 characters)
        confirm_password: Password confirmation
        submit: Submit button
    """
    
    username = StringField(
        'Username',
        validators=[
            DataRequired(message='Username is required.'),
            Length(min=3, max=20, message='Username must be between 3 and 20 characters.'),
            Regexp(
                '^[a-zA-Z0-9_]+$',
                message='Username can only contain letters, numbers, and underscores.'
            )
        ],
        render_kw={'placeholder': 'Enter username', 'class': 'form-control'}
    )
    
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email is required.'),
            Email(message='Please enter a valid email address.'),
            Length(max=120, message='Email must be less than 120 characters.')
        ],
        render_kw={'placeholder': 'Enter email address', 'class': 'form-control', 'type': 'email'}
    )
    
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.'),
            Length(min=8, message='Password must be at least 8 characters long.')
        ],
        render_kw={'placeholder': 'Enter password (min. 8 characters)', 'class': 'form-control'}
    )
    
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password.'),
            EqualTo('password', message='Passwords must match.')
        ],
        render_kw={'placeholder': 'Confirm password', 'class': 'form-control'}
    )
    
    submit = SubmitField(
        'Register',
        render_kw={'class': 'btn btn-success w-100'}
    )
    
    def validate_username(self, field):
        """
        Custom validator to check if username is unique.
        
        Args:
            field: The username field
            
        Raises:
            ValidationError: If username already exists
        """
        if User.username_exists(field.data):
            raise ValidationError('This username is already taken. Please choose a different one.')
    
    def validate_email(self, field):
        """
        Custom validator to check if email is unique.
        
        Args:
            field: The email field
            
        Raises:
            ValidationError: If email already exists
        """
        if User.email_exists(field.data):
            raise ValidationError('This email address is already registered. Please use a different email or try logging in.')


class ChangePasswordForm(FlaskForm):
    """
    Form for changing user password (future enhancement).
    
    Fields:
        current_password: Current password for verification
        new_password: New password (minimum 8 characters)
        confirm_password: New password confirmation
        submit: Submit button
    """
    
    current_password = PasswordField(
        'Current Password',
        validators=[
            DataRequired(message='Current password is required.')
        ],
        render_kw={'placeholder': 'Enter current password', 'class': 'form-control'}
    )
    
    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message='New password is required.'),
            Length(min=8, message='Password must be at least 8 characters long.')
        ],
        render_kw={'placeholder': 'Enter new password (min. 8 characters)', 'class': 'form-control'}
    )
    
    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(message='Please confirm your new password.'),
            EqualTo('new_password', message='Passwords must match.')
        ],
        render_kw={'placeholder': 'Confirm new password', 'class': 'form-control'}
    )
    
    submit = SubmitField(
        'Change Password',
        render_kw={'class': 'btn btn-primary w-100'}
    )
