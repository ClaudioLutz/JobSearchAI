"""
Pytest Configuration and Shared Fixtures
Provides reusable test fixtures for all test modules.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash


@pytest.fixture(scope='session')
def app():
    """
    Create Flask application for testing.
    
    Yields:
        Flask: Configured test application
    """
    app = Flask(__name__)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False
    })
    
    # Initialize database
    from models import db
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def db_session(app):
    """
    Create a database session for testing.
    
    Args:
        app: Flask application fixture
        
    Yields:
        SQLAlchemy session
    """
    from models import db
    
    with app.app_context():
        # Start transaction
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Bind session to connection
        session = db.create_scoped_session(
            options={'bind': connection, 'binds': {}}
        )
        db.session = session
        
        yield session
        
        # Rollback transaction
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(app):
    """
    Create test client.
    
    Args:
        app: Flask application fixture
        
    Returns:
        FlaskClient: Test client
    """
    return app.test_client()


@pytest.fixture
def temp_workspace():
    """
    Create temporary workspace with standard directory structure.
    
    Yields:
        Path: Temporary workspace directory
    """
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)
    
    # Create standard directory structure
    (workspace / 'job_matches').mkdir()
    (workspace / 'job_matches' / 'pending').mkdir()
    (workspace / 'job_matches' / 'sent').mkdir()
    (workspace / 'job_matches' / 'failed').mkdir()
    (workspace / 'job_matches' / 'backups').mkdir()
    (workspace / 'motivation_letters').mkdir()
    (workspace / 'job-data-acquisition').mkdir()
    (workspace / 'job-data-acquisition' / 'data').mkdir()
    
    yield workspace
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_match():
    """
    Sample job match data.
    
    Returns:
        dict: Match data
    """
    return {
        'job_title': 'Senior Software Engineer',
        'company_name': 'TechCorp AG',
        'application_url': 'https://techcorp.com/jobs/12345',
        'location': 'Zürich, Switzerland',
        'overall_match': 8,
        'cv_path': 'cv/resume.pdf',
        'job_description': 'We are looking for an experienced software engineer...' * 10,
        'required_skills': ['Python', 'Docker', 'AWS'],
        'preferred_skills': ['Kubernetes', 'CI/CD'],
        'scraped_at': datetime.now().isoformat()
    }


@pytest.fixture
def sample_letter():
    """
    Sample motivation letter data.
    
    Returns:
        dict: Letter data
    """
    return {
        'job_title': 'Senior Software Engineer',
        'company_name': 'TechCorp AG',
        'application_url': 'https://techcorp.com/jobs/12345',
        'subject': 'Bewerbung als Senior Software Engineer',
        'greeting': 'Sehr geehrte Damen und Herren',
        'introduction': 'Mit großem Interesse habe ich Ihre Stellenausschreibung...',
        'body_paragraphs': [
            'In meiner aktuellen Position konnte ich umfangreiche Erfahrungen sammeln...',
            'Besonders reizvoll finde ich die Möglichkeit...',
            'Meine Kenntnisse in Python und Docker...'
        ],
        'closing': 'Über eine Einladung zu einem persönlichen Gespräch würde ich mich sehr freuen',
        'signature': 'Mit freundlichen Grüßen',
        'full_name': 'Max Mustermann'
    }


@pytest.fixture
def sample_scraped_data():
    """
    Sample scraped job data.
    
    Returns:
        dict: Scraped data
    """
    return {
        'Job Title': 'Senior Software Engineer',
        'Company Name': 'TechCorp AG',
        'Application URL': 'https://techcorp.com/jobs/12345',
        'Contact Person': 'Frau Dr. Müller',
        'Contact Email': 'jobs@techcorp.com',
        'Email': 'recruiting@techcorp.com',
        'Job Description': 'We are looking for an experienced software engineer to join our team. ' * 20,
        'Requirements': 'Bachelor in Computer Science, 5+ years experience...',
        'Location': 'Zürich, Switzerland',
        'Employment Type': 'Full-time',
        'Posted Date': '2025-10-15',
        'Scraped At': datetime.now().isoformat()
    }


@pytest.fixture
def sample_queue_application():
    """
    Sample queue application data.
    
    Returns:
        dict: Queue application
    """
    return {
        'id': 'app-test-12345',
        'job_title': 'Senior Software Engineer',
        'company_name': 'TechCorp AG',
        'recipient_email': 'jobs@techcorp.com',
        'recipient_name': 'Frau Dr. Müller',
        'subject_line': 'Bewerbung als Senior Software Engineer',
        'motivation_letter': '<p>Sehr geehrte Damen und Herren,</p>' * 10,
        'email_text': 'Plain text version of email...',
        'application_url': 'https://techcorp.com/jobs/12345',
        'match_score': 8,
        'location': 'Zürich, Switzerland',
        'created_at': datetime.now().isoformat(),
        'status': 'pending',
        'requires_manual_email': False
    }


@pytest.fixture
def sample_user_data():
    """
    Sample user registration data.
    
    Returns:
        dict: User data
    """
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'SecurePassword123!',
        'password_hash': generate_password_hash('SecurePassword123!')
    }


@pytest.fixture
def create_test_files(temp_workspace):
    """
    Factory fixture to create test files in workspace.
    
    Args:
        temp_workspace: Temporary workspace fixture
        
    Returns:
        Callable: Function to create test files
    """
    def _create_files(match_data=None, letter_data=None, scraped_data=None):
        """
        Create test files in workspace.
        
        Args:
            match_data: Match data to write
            letter_data: Letter data to write
            scraped_data: Scraped data to write
            
        Returns:
            dict: Paths to created files
        """
        paths = {}
        
        if match_data:
            match_file = temp_workspace / 'job_matches' / 'test_matches.json'
            with open(match_file, 'w', encoding='utf-8') as f:
                json.dump([match_data], f, indent=2, ensure_ascii=False)
            paths['match'] = match_file
        
        if letter_data:
            letter_dir = temp_workspace / 'motivation_letters' / 'test_company'
            letter_dir.mkdir(parents=True, exist_ok=True)
            
            letter_json = letter_dir / 'letter.json'
            with open(letter_json, 'w', encoding='utf-8') as f:
                json.dump(letter_data, f, indent=2, ensure_ascii=False)
            paths['letter_json'] = letter_json
            
            # Create HTML version
            letter_html = letter_dir / 'letter.html'
            html_content = f"""
            <p>{letter_data.get('greeting', '')},</p>
            <p>{letter_data.get('introduction', '')}</p>
            {''.join(f'<p>{p}</p>' for p in letter_data.get('body_paragraphs', []))}
            <p>{letter_data.get('closing', '')}</p>
            <p>{letter_data.get('signature', '')},<br>{letter_data.get('full_name', '')}</p>
            """
            with open(letter_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            paths['letter_html'] = letter_html
        
        if scraped_data:
            scraped_file = temp_workspace / 'job-data-acquisition' / 'data' / 'scraped_job.json'
            with open(scraped_file, 'w', encoding='utf-8') as f:
                json.dump(scraped_data, f, indent=2, ensure_ascii=False)
            paths['scraped'] = scraped_file
        
        return paths
    
    return _create_files


@pytest.fixture
def mock_env_credentials(monkeypatch):
    """
    Mock environment variables for Gmail credentials.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    monkeypatch.setenv('GMAIL_ADDRESS', 'test@gmail.com')
    monkeypatch.setenv('GMAIL_APP_PASSWORD', 'test_app_password')
    monkeypatch.setenv('OPENAI_API_KEY', 'test_openai_key')


# Parametrize helpers

@pytest.fixture(params=['valid', 'invalid_email', 'missing_fields', 'empty'])
def application_variants(request, sample_queue_application):
    """
    Provide various application data variants for parametrized tests.
    
    Args:
        request: Pytest request fixture
        sample_queue_application: Sample application fixture
        
    Returns:
        tuple: (variant_name, application_data, expected_valid)
    """
    variant = request.param
    
    if variant == 'valid':
        return ('valid', sample_queue_application.copy(), True)
    
    elif variant == 'invalid_email':
        app = sample_queue_application.copy()
        app['recipient_email'] = 'invalid-email'
        return ('invalid_email', app, False)
    
    elif variant == 'missing_fields':
        app = sample_queue_application.copy()
        del app['job_title']
        del app['company_name']
        return ('missing_fields', app, False)
    
    elif variant == 'empty':
        return ('empty', {}, False)
