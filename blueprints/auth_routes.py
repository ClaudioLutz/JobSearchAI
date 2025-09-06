"""
Authentication routes for JobSearchAI application.
Handles user login, registration, and logout functionality.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db
from models.user import User
from forms.auth_forms import LoginForm, RegistrationForm

# Create authentication blueprint
auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login with username or email.
    
    GET: Display login form
    POST: Process login credentials and authenticate user
    
    Returns:
        Rendered login template or redirect to dashboard/intended page
    """
    # Redirect authenticated users to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Find user by username or email
        user = User.find_by_username_or_email(form.username_or_email.data)
        
        # Verify password
        if user and user.check_password(form.password.data):
            # Check if account is active
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'error')
                return render_template('auth/login.html', title='Sign In', form=form)
            
            # Login user with Flask-Login
            login_user(user, remember=form.remember_me.data)
            
            # Update last login timestamp
            user.update_last_login()
            
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirect to intended page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username/email or password.', 'error')
    
    return render_template('auth/login.html', title='Sign In', form=form)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    
    GET: Display registration form
    POST: Process registration data and create new user account
    
    Returns:
        Rendered registration template or redirect to dashboard after successful registration
    """
    # Redirect authenticated users to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            # Create new user
            user = User()
            user.username = form.username.data.lower().strip() if form.username.data else ""
            user.email = form.email.data.lower().strip() if form.email.data else ""
            user.set_password(form.password.data)
            
            # Add to database
            db.session.add(user)
            db.session.commit()
            
            # Auto-login the new user
            login_user(user)
            user.update_last_login()
            
            flash(f'Welcome to JobSearchAI, {user.username}! Your account has been created successfully.', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            # Log the error for debugging
            print(f"Registration error: {e}")
    
    return render_template('auth/register.html', title='Register', form=form)


@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Handle user logout.
    
    POST: Clear user session and redirect to login page
    
    Returns:
        Redirect to login page with success message
    """
    username = current_user.username
    logout_user()
    flash(f'You have been logged out successfully, {username}.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/logout-get')
@login_required
def logout_get():
    """
    Handle GET requests to logout (for convenience links).
    
    GET: Clear user session and redirect to login page
    
    Returns:
        Redirect to login page with success message
    """
    username = current_user.username
    logout_user()
    flash(f'You have been logged out successfully, {username}.', 'info')
    return redirect(url_for('auth.login'))


# Error handlers specific to authentication
@auth.errorhandler(401)
def unauthorized(error):
    """
    Handle unauthorized access attempts.
    
    Args:
        error: The 401 error object
        
    Returns:
        Redirect to login page with appropriate message
    """
    flash('Please log in to access this page.', 'info')
    return redirect(url_for('auth.login'))


@auth.errorhandler(403)
def forbidden(error):
    """
    Handle forbidden access attempts.
    
    Args:
        error: The 403 error object
        
    Returns:
        Rendered error template or redirect to dashboard
    """
    if current_user.is_authenticated:
        flash('You do not have permission to access this resource.', 'error')
        return redirect(url_for('index'))
    else:
        flash('Please log in to access this page.', 'info')
        return redirect(url_for('auth.login'))
