"""
Unit tests for authentication routes
"""
import pytest
import json
from flask import url_for


class TestAuth:
    """Test authentication endpoints"""
    
    def test_register_success(self, client, db_session):
        """Test successful user registration"""
        data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'reg_no': 'NEW001',
            'college_email': 'newuser@audisankara.ac.in',
            'password': 'password123',
            'role': 'student'
        }
        
        response = client.post(
            '/api/auth/register',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'user' in data
        assert data['user']['username'] == 'newuser'
    
    def test_register_duplicate_username(self, client, db_session, test_user):
        """Test registration with duplicate username"""
        data = {
            'username': 'testuser',  # Already exists
            'first_name': 'Test',
            'last_name': 'User',
            'reg_no': 'NEW002',
            'college_email': 'newuser2@audisankara.ac.in',
            'password': 'password123',
            'role': 'student'
        }
        
        response = client.post(
            '/api/auth/register',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_register_invalid_email(self, client, db_session):
        """Test registration with invalid email"""
        data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'reg_no': 'NEW001',
            'college_email': 'invalid@email.com',  # Not @audisankara.ac.in
            'password': 'password123',
            'role': 'student'
        }
        
        response = client.post(
            '/api/auth/register',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = client.post(
            '/api/auth/login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert 'user' in data
        assert data['user']['username'] == 'testuser'
    
    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = client.post(
            '/api/auth/login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'remaining_attempts' in data
    
    def test_login_brute_force_protection(self, client, test_user):
        """Test brute force protection after multiple failed attempts"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        # Make 5 failed attempts
        for i in range(5):
            response = client.post(
                '/api/auth/login',
                data=json.dumps(data),
                content_type='application/json'
            )
            assert response.status_code == 401
        
        # 6th attempt should be blocked
        response = client.post(
            '/api/auth/login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 429
        data = json.loads(response.data)
        assert 'error' in data
        assert 'lockout_remaining' in data
    
    def test_refresh_token_success(self, client, app, test_user, refresh_token):
        """Test successful token refresh"""
        with app.app_context():
            response = client.post(
                '/api/auth/refresh',
                data=json.dumps({'refresh_token': refresh_token}),
                content_type='application/json',
                headers={'Authorization': f'Bearer {refresh_token}'}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'access_token' in data
            assert 'expires_in' in data
    
    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid token"""
        response = client.post(
            '/api/auth/refresh',
            data=json.dumps({'refresh_token': 'invalid_token'}),
            content_type='application/json',
            headers={'Authorization': 'Bearer invalid_token'}
        )
        
        assert response.status_code == 401
    
    def test_get_current_user(self, client, auth_headers, test_user):
        """Test getting current user info"""
        response = client.get(
            '/api/auth/me',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data
        assert data['user']['username'] == 'testuser'
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without token"""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401
    
    def test_logout(self, client, auth_headers):
        """Test logout"""
        response = client.post(
            '/api/auth/logout',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
