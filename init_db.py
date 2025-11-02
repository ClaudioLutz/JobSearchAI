"""
Database initialization script for JobSearchAI authentication system.

This script handles database creation, migrations, and initial setup.
"""

import os
import sys
from flask import Flask
from flask_migrate import Migrate, init, migrate, upgrade
from sqlalchemy import text
from config import get_database_config, get_secret_key
from models import db, User
from utils.db_utils import JobMatchDatabase


def create_app():
    """
    Create Flask application with database configuration.
    
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    # Database configuration
    db_config = get_database_config()
    if not db_config.get('SQLALCHEMY_DATABASE_URI'):
        print("ERROR: Database configuration not found!")
        print("Please set DATABASE_URL or individual DB_* environment variables.")
        sys.exit(1)
    
    app.config.update(db_config)
    
    # Secret key configuration
    secret_key = get_secret_key()
    if not secret_key:
        print("ERROR: SECRET_KEY environment variable not found!")
        print("Please set SECRET_KEY in your environment variables.")
        sys.exit(1)
    
    app.config['SECRET_KEY'] = secret_key
    
    # Initialize extensions
    db.init_app(app)
    
    return app


def init_migrations(app):
    """
    Initialize Flask-Migrate for the application.
    
    Args:
        app (Flask): Flask application instance
    """
    migrate_instance = Migrate(app, db)
    
    with app.app_context():
        if not os.path.exists('migrations'):
            print("Initializing migrations...")
            init()
            print("Migrations initialized successfully!")
        else:
            print("Migrations directory already exists.")
    
    return migrate_instance


def create_migration(app, message="Auto migration"):
    """
    Create a new migration.
    
    Args:
        app (Flask): Flask application instance
        message (str): Migration message
    """
    migrate_instance = Migrate(app, db)
    
    with app.app_context():
        print(f"Creating migration: {message}")
        migrate(message=message)
        print("Migration created successfully!")


def run_migrations(app):
    """
    Run pending migrations.
    
    Args:
        app (Flask): Flask application instance
    """
    migrate_instance = Migrate(app, db)
    
    with app.app_context():
        print("Running database migrations...")
        upgrade()
        print("Migrations completed successfully!")


def create_tables(app):
    """
    Create all database tables (alternative to migrations).
    
    Args:
        app (Flask): Flask application instance
    """
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")


def create_admin_user(app, username="admin", email="admin@jobsearchai.local", password="admin123"):
    """
    Create an admin user for testing purposes.
    
    Args:
        app (Flask): Flask application instance
        username (str): Admin username
        email (str): Admin email
        password (str): Admin password
    """
    with app.app_context():
        # Check if admin user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            # If user exists but is not admin, promote to admin
            if not existing_user.is_admin:
                existing_user.is_admin = True
                db.session.commit()
                print(f"User '{username}' promoted to admin!")
            else:
                print(f"Admin user '{username}' already exists!")
            return
        
        # Create admin user
        admin_user = User()
        admin_user.username = username
        admin_user.email = email
        admin_user.set_password(password)
        admin_user.is_admin = True  # Set admin privileges
        
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"Admin user '{username}' created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Admin privileges: Yes")
        print("IMPORTANT: Change the admin password after first login!")


def check_database_connection(app):
    """
    Test database connection.
    
    Args:
        app (Flask): Flask application instance
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with app.app_context():
            # Try to execute a simple query
            db.session.execute(text('SELECT 1'))
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


def init_job_match_database(db_path: str = "instance/jobsearchai.db"):
    """
    Initialize the job matching database schema.
    
    Args:
        db_path: Path to SQLite database file
    """
    print(f"Initializing job matching database at {db_path}...")
    
    try:
        db = JobMatchDatabase(db_path)
        db.connect()
        db.init_database()
        db.close()
        print("Job matching database initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize job matching database: {e}")
        sys.exit(1)


def main():
    """Main initialization function."""
    print("JobSearchAI Database Initialization")
    print("=" * 40)
    
    # Create Flask app
    app = create_app()
    
    # Test database connection
    if not check_database_connection(app):
        print("Exiting due to database connection failure.")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "init":
            # Initialize migrations
            init_migrations(app)
            
        elif command == "migrate":
            # Create migration
            message = sys.argv[2] if len(sys.argv) > 2 else "Auto migration"
            create_migration(app, message)
            
        elif command == "upgrade":
            # Run migrations
            run_migrations(app)
            
        elif command == "create-tables":
            # Create tables without migrations
            create_tables(app)
            
        elif command == "create-admin":
            # Create admin user
            username = sys.argv[2] if len(sys.argv) > 2 else "admin"
            email = sys.argv[3] if len(sys.argv) > 3 else "admin@jobsearchai.local"
            password = sys.argv[4] if len(sys.argv) > 4 else "admin123"
            create_admin_user(app, username, email, password)
            
        elif command == "full-setup":
            # Full setup: init, migrate, upgrade, create admin
            print("Running full database setup...")
            init_migrations(app)
            create_migration(app, "Initial migration")
            run_migrations(app)
            create_admin_user(app)
            print("Full setup completed!")
            
        elif command == "init-job-db":
            # Initialize job matching database
            db_path = sys.argv[2] if len(sys.argv) > 2 else "instance/jobsearchai.db"
            init_job_match_database(db_path)
            
        else:
            print(f"Unknown command: {command}")
            print_usage()
    else:
        print_usage()


def print_usage():
    """Print usage instructions."""
    print("\nUsage: python init_db.py <command> [options]")
    print("\nCommands:")
    print("  init                    - Initialize migrations")
    print("  migrate [message]       - Create new migration")
    print("  upgrade                 - Run pending migrations")
    print("  create-tables          - Create tables without migrations")
    print("  create-admin [u] [e] [p] - Create admin user")
    print("  full-setup             - Complete database setup")
    print("  init-job-db [path]     - Initialize job matching database (default: instance/jobsearchai.db)")
    print("\nExamples:")
    print("  python init_db.py init")
    print("  python init_db.py migrate 'Add user table'")
    print("  python init_db.py upgrade")
    print("  python init_db.py create-admin myuser user@example.com mypassword")
    print("  python init_db.py full-setup")
    print("  python init_db.py init-job-db")
    print("  python init_db.py init-job-db instance/custom.db")


if __name__ == "__main__":
    main()
