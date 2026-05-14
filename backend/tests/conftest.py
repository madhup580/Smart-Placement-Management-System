"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys
from flask import Flask
from flask_jwt_extended import create_access_token, create_refresh_token

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User
from config import Config


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    # Use test configuration
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'REDIS_URL': None,  # Disable Redis for tests
    }
    
    app = create_app('development')
    app.config.update(test_config)
    
    # Create test database
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create CLI test runner"""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for testing"""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        username='testuser',
        first_name='Test',
        last_name='User',
        reg_no='TEST001',
        college_email='test@audisankara.ac.in',
        email='test@audisankara.ac.in',
        role='student',
        full_name='Test User',
        is_active=True
    )
    user.set_password('testpass123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_faculty(db_session):
    """Create a test faculty user"""
    user = User(
        username='testfaculty',
        first_name='Test',
        last_name='Faculty',
        reg_no='FAC001',
        college_email='faculty@audisankara.ac.in',
        email='faculty@audisankara.ac.in',
        role='faculty',
        full_name='Test Faculty',
        is_active=True
    )
    user.set_password('testpass123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(app, test_user):
    """Create authentication headers for test user"""
    with app.app_context():
        access_token = create_access_token(identity=str(test_user.id))
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }


@pytest.fixture
def refresh_token(app, test_user):
    """Create refresh token for test user"""
    with app.app_context():
        return create_refresh_token(identity=str(test_user.id))
