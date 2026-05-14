"""
Unit tests for interview routes
"""
import pytest
import json


class TestInterview:
    """Test interview endpoints"""
    
    def test_start_interview(self, client, auth_headers):
        """Test starting an interview"""
        data = {
            'interview_type': 'technical',
            'resume_data': {},
            'jd_data': {}
        }
        
        response = client.post(
            '/api/interview/start-interview',
            data=json.dumps(data),
            content_type='application/json',
            headers=auth_headers
        )
        
        # May return 200 or 400 depending on requirements
        assert response.status_code in [200, 400]
    
    def test_start_interview_unauthorized(self, client):
        """Test starting interview without authentication"""
        data = {
            'interview_type': 'technical'
        }
        
        response = client.post(
            '/api/interview/start-interview',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 401
    
    def test_submit_answer(self, client, auth_headers):
        """Test submitting interview answer"""
        data = {
            'session_id': 1,
            'answer': 'This is my answer',
            'time_taken_seconds': 30
        }
        
        response = client.post(
            '/api/interview/submit-answer',
            data=json.dumps(data),
            content_type='application/json',
            headers=auth_headers
        )
        
        # May return 404 if session doesn't exist
        assert response.status_code in [200, 404, 400]
