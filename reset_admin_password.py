#!/usr/bin/env python3
"""
Simple script to reset admin user password in JobSearchAI.
"""

import sys
from flask import Flask
from models import db, User
from config import get_secret_key, get_database_config


def create_app():
    """Create Flask app for password reset"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = get_secret_key()
    app.config.update(get_database_config())
    db.init_app(app)
    return app


def reset_password(username_or_email, new_password):
    """Reset password for a user"""
    app = create_app()
    
    with app.app_context():
        try:
            user = User.find_by_username_or_email(username_or_email)
            if not user:
                print(f"✗ User not found: {username_or_email}")
                return False
            
            user.set_password(new_password)
            db.session.commit()
            
            print(f"✓ Password reset successful for user: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Admin: {'Yes' if user.is_admin else 'No'}")
            print(f"  New password: {new_password}")
            return True
            
        except Exception as e:
            print(f"✗ Error resetting password: {e}")
            db.session.rollback()
            return False


def main():
    """Main function"""
    print("JobSearchAI Password Reset Tool")
    print("=" * 40)
    
    if len(sys.argv) < 3:
        print("\nUsage: python reset_admin_password.py <username_or_email> <new_password>")
        print("\nExamples:")
        print("  python reset_admin_password.py admin newpassword123")
        print("  python reset_admin_password.py admin@jobsearchai.local SecurePass456!")
        print("  python reset_admin_password.py claudio mypassword")
        sys.exit(1)
    
    username_or_email = sys.argv[1]
    new_password = sys.argv[2]
    
    if len(new_password) < 6:
        print("✗ Password must be at least 6 characters long")
        sys.exit(1)
    
    success = reset_password(username_or_email, new_password)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
