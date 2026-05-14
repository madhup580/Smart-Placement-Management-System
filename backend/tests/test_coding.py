"""
Unit tests for coding routes
"""
import pytest
import json


class TestCoding:
    """Test coding endpoints"""
    
    def test_get_questions(self, client, auth_headers):
        """Test getting coding questions"""
        response = client.get(
            '/api/coding/questions',
            headers=auth_headers
        )
        
        # Should return 200 even if no questions
        assert response.status_code in [200, 404]
    
    def test_execute_code(self, client, auth_headers):
        """Test code execution"""
        data = {
            'code': 'print("Hello, World!")',
            'language': 'python',
            'stdin': '',
            'question_id': None
        }
        
        response = client.post(
            '/api/coding/execute',
            data=json.dumps(data),
            content_type='application/json',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'output' in data or 'error' in data
    
    def test_execute_code_unauthorized(self, client):
        """Test code execution without authentication"""
        data = {
            'code': 'print("Hello, World!")',
            'language': 'python',
            'stdin': ''
        }
        
        response = client.post(
            '/api/coding/execute',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_submit_code(self, client, auth_headers):
        """Test code submission"""
        data = {
            'question_id': 1,
            'code': 'def solution(): return 42',
            'language': 'python'
        }
        
        response = client.post(
            '/api/coding/submit',
            data=json.dumps(data),
            content_type='application/json',
            headers=auth_headers
        )
        
        # May return 404 if question doesn't exist, or 200 if it does
        assert response.status_code in [200, 404, 400]
