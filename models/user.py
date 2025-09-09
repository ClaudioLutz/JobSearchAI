"""
User model for JobSearchAI authentication system.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):
    """
    User model for authentication.
    
    Attributes:
        id: Primary key
        username: Unique username (3-20 characters, alphanumeric + underscore)
        email: Unique email address
        password_hash: Hashed password using Werkzeug
        created_at: Account creation timestamp
        last_login: Last login timestamp
        is_active: Account status (active/inactive)
    """
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    
    def __repr__(self):
        """String representation of User object."""
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """
        Hash and set the user's password.
        
        Args:
            password (str): Plain text password
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Check if provided password matches the user's password.
        
        Args:
            password (str): Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update the last_login timestamp to current time."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def find_by_username_or_email(identifier):
        """
        Find user by username or email.
        
        Args:
            identifier (str): Username or email address
            
        Returns:
            User or None: User object if found, None otherwise
        """
        return User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
    
    @staticmethod
    def username_exists(username):
        """
        Check if username already exists.
        
        Args:
            username (str): Username to check
            
        Returns:
            bool: True if username exists, False otherwise
        """
        return User.query.filter_by(username=username).first() is not None
    
    @staticmethod
    def email_exists(email):
        """
        Check if email already exists.
        
        Args:
            email (str): Email to check
            
        Returns:
            bool: True if email exists, False otherwise
        """
        return User.query.filter_by(email=email).first() is not None
    
    def to_dict(self):
        """
        Convert user object to dictionary (excluding sensitive data).
        
        Returns:
            dict: User data dictionary
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }
    
    # Flask-Login required methods
    def get_id(self):
        """Return the user ID as a string (required by Flask-Login)."""
        return str(self.id)
    
    @property
    def is_authenticated(self):
        """Return True if user is authenticated (required by Flask-Login)."""
        return True
    
    @property
    def is_anonymous(self):
        """Return False as this is not an anonymous user (required by Flask-Login)."""
        return False
