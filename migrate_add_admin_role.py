#!/usr/bin/env python3
"""
Database migration script to add admin role to existing users.
This script adds the is_admin column to the users table and provides
functionality to promote users to admin status.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append('.')

from flask import Flask
from models import db
from models.user import User
from config import get_secret_key, get_database_config


def create_app():
    """Create Flask app for migration"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = get_secret_key()
    app.config.update(get_database_config())
    
    db.init_app(app)
    return app


def migrate_database():
    """Add is_admin column to users table if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        # Check if is_admin column already exists
        try:
            # Try to query for is_admin column
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT is_admin FROM users LIMIT 1"))
            print("✓ is_admin column already exists in users table")
            return True
        except Exception:
            # Column doesn't exist, create it
            print("Adding is_admin column to users table...")
            try:
                # Add the column with default value False
                with db.engine.connect() as conn:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE"))
                    conn.commit()
                print("✓ Successfully added is_admin column")
                return True
            except Exception as e:
                print(f"✗ Error adding is_admin column: {e}")
                return False


def list_users():
    """List all users with their admin status"""
    app = create_app()
    
    with app.app_context():
        try:
            users = User.query.all()
            print("\n=== Current Users ===")
            print(f"{'ID':<4} {'Username':<20} {'Email':<30} {'Admin':<8} {'Active':<8}")
            print("-" * 72)
            
            for user in users:
                admin_status = "Yes" if getattr(user, 'is_admin', False) else "No"
                active_status = "Yes" if user.is_active else "No"
                print(f"{user.id:<4} {user.username:<20} {user.email:<30} {admin_status:<8} {active_status:<8}")
            
            if not users:
                print("No users found in database")
            
            return users
        except Exception as e:
            print(f"✗ Error listing users: {e}")
            return []


def promote_user_to_admin(username_or_email):
    """Promote a user to admin status"""
    app = create_app()
    
    with app.app_context():
        try:
            user = User.find_by_username_or_email(username_or_email)
            if not user:
                print(f"✗ User not found: {username_or_email}")
                return False
            
            if getattr(user, 'is_admin', False):
                print(f"✓ User {user.username} is already an admin")
                return True
            
            user.is_admin = True
            db.session.commit()
            print(f"✓ Successfully promoted {user.username} to admin")
            return True
            
        except Exception as e:
            print(f"✗ Error promoting user to admin: {e}")
            db.session.rollback()
            return False


def demote_admin_user(username_or_email):
    """Remove admin privileges from a user"""
    app = create_app()
    
    with app.app_context():
        try:
            user = User.find_by_username_or_email(username_or_email)
            if not user:
                print(f"✗ User not found: {username_or_email}")
                return False
            
            if not getattr(user, 'is_admin', False):
                print(f"✓ User {user.username} is not an admin")
                return True
            
            user.is_admin = False
            db.session.commit()
            print(f"✓ Successfully removed admin privileges from {user.username}")
            return True
            
        except Exception as e:
            print(f"✗ Error removing admin privileges: {e}")
            db.session.rollback()
            return False


def interactive_mode():
    """Interactive mode for managing admin users"""
    print("\n=== Admin User Management ===")
    print("1. List all users")
    print("2. Promote user to admin")
    print("3. Remove admin privileges")
    print("4. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            list_users()
        elif choice == '2':
            username_or_email = input("Enter username or email to promote: ").strip()
            if username_or_email:
                promote_user_to_admin(username_or_email)
            else:
                print("✗ Invalid input")
        elif choice == '3':
            username_or_email = input("Enter username or email to demote: ").strip()
            if username_or_email:
                demote_admin_user(username_or_email)
            else:
                print("✗ Invalid input")
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("✗ Invalid choice. Please enter 1-4.")


def main():
    """Main migration function"""
    print("JobSearchAI Admin Role Migration")
    print("=================================")
    
    # First, run the database migration
    if not migrate_database():
        print("✗ Migration failed. Exiting.")
        return 1
    
    # Show current users
    users = list_users()
    
    if len(sys.argv) > 1:
        # Command line mode
        command = sys.argv[1].lower()
        
        if command == 'list':
            # Already listed above
            pass
        elif command == 'promote' and len(sys.argv) > 2:
            username_or_email = sys.argv[2]
            promote_user_to_admin(username_or_email)
        elif command == 'demote' and len(sys.argv) > 2:
            username_or_email = sys.argv[2]
            demote_admin_user(username_or_email)
        else:
            print("\nUsage:")
            print(f"  {sys.argv[0]} list                    # List all users")
            print(f"  {sys.argv[0]} promote <username>      # Promote user to admin")
            print(f"  {sys.argv[0]} demote <username>       # Remove admin privileges")
            print(f"  {sys.argv[0]}                         # Interactive mode")
            return 1
    else:
        # Interactive mode
        if users:
            print(f"\nFound {len(users)} user(s) in database.")
            admin_count = sum(1 for u in users if getattr(u, 'is_admin', False))
            print(f"Current admin users: {admin_count}")
            
            if admin_count == 0:
                print("\n⚠️  WARNING: No admin users found!")
                print("   You should promote at least one user to admin to access AI features.")
        
        interactive_mode()
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
