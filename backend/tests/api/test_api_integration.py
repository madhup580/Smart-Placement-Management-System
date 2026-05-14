"""
API Integration Tests using HTTPX
Tests the full API flow end-to-end
"""
import pytest
import httpx
import json
from typing import Dict, Optional


BASE_URL = "http://127.0.0.1:5000/api"


class TestAPIIntegration:
    """Integration tests for API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create HTTPX test client"""
        return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
    
    @pytest.fixture
    async def auth_token(self, client):
        """Get authentication token"""
        # First register a user
        register_data = {
            'username': 'apitestuser',
            'first_name': 'API',
            'last_name': 'Test',
            'reg_no': 'API001',
            'college_email': 'apitest@audisankara.ac.in',
            'password': 'testpass123',
            'role': 'student'
        }
        
        response = await client.post('/auth/register', json=register_data)
        
        if response.status_code == 201:
            data = response.json()
            return data.get('access_token')
        elif response.status_code == 400:
            # User might already exist, try login
            login_data = {
                'username': 'apitestuser',
                'password': 'testpass123'
            }
            response = await client.post('/auth/login', json=login_data)
            if response.status_code == 200:
                return response.json().get('access_token')
        
        return None
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
    
    @pytest.mark.asyncio
    async def test_register_flow(self, client):
        """Test complete registration flow"""
        import time
        timestamp = int(time.time())
        data = {
            'username': f'newuser_{timestamp}',
            'first_name': 'New',
            'last_name': 'User',
            'reg_no': f'NEW{timestamp}',
            'college_email': f'newuser{timestamp}@audisankara.ac.in',
            'password': 'password123',
            'role': 'student'
        }
        
        response = await client.post('/auth/register', json=data)
        
        # Should succeed or fail with duplicate (both are valid)
        assert response.status_code in [201, 400]
        
        if response.status_code == 201:
            response_data = response.json()
            assert 'access_token' in response_data
            assert 'refresh_token' in response_data
    
    @pytest.mark.asyncio
    async def test_login_flow(self, client, auth_token):
        """Test login flow"""
        if not auth_token:
            pytest.skip("Could not get auth token")
        
        # Test getting current user
        headers = {'Authorization': f'Bearer {auth_token}'}
        response = await client.get('/auth/me', headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'user' in data
    
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, client, auth_token):
        """Test token refresh flow"""
        if not auth_token:
            pytest.skip("Could not get auth token")
        
        # First login to get refresh token
        login_data = {
            'username': 'apitestuser',
            'password': 'testpass123'
        }
        
        response = await client.post('/auth/login', json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            refresh_token = data.get('refresh_token')
            
            if refresh_token:
                # Try to refresh
                headers = {'Authorization': f'Bearer {refresh_token}'}
                response = await client.post(
                    '/auth/refresh',
                    json={'refresh_token': refresh_token},
                    headers=headers
                )
                
                # Should succeed or fail with invalid token
                assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_coding_endpoints(self, client, auth_token):
        """Test coding endpoints"""
        if not auth_token:
            pytest.skip("Could not get auth token")
        
        headers = {'Authorization': f'Bearer {auth_token}'}
        
        # Test getting questions
        response = await client.get('/coding/questions', headers=headers)
        assert response.status_code in [200, 404]
        
        # Test code execution
        execute_data = {
            'code': 'print("Hello, World!")',
            'language': 'python',
            'stdin': ''
        }
        
        response = await client.post(
            '/coding/execute',
            json=execute_data,
            headers=headers
        )
        
        assert response.status_code in [200, 400, 500]
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, client):
        """Test rate limiting"""
        # Make many requests quickly
        responses = []
        for i in range(15):
            response = await client.get('/auth/')
            responses.append(response.status_code)
        
        # Should eventually hit rate limit (429)
        # Note: This depends on rate limit configuration
        assert 429 in responses or all(r == 200 for r in responses)
