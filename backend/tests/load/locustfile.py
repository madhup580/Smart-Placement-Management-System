"""
Locust load testing configuration
Run with: locust -f tests/load/locustfile.py --host=http://localhost:5000
"""
from locust import HttpUser, task, between
import random
import json


class APIUser(HttpUser):
    """Simulate API user behavior"""
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Register or login
        self.username = f"loadtest_{random.randint(1000, 9999)}"
        self.password = "testpass123"
        self.token = None
        
        # Try to register
        register_data = {
            'username': self.username,
            'first_name': 'Load',
            'last_name': 'Test',
            'reg_no': f'LOAD{random.randint(1000, 9999)}',
            'college_email': f'{self.username}@audisankara.ac.in',
            'password': self.password,
            'role': 'student'
        }
        
        response = self.client.post('/api/auth/register', json=register_data)
        
        if response.status_code == 201:
            data = response.json()
            self.token = data.get('access_token')
        elif response.status_code == 400:
            # User exists, try login
            login_data = {
                'username': self.username,
                'password': self.password
            }
            response = self.client.post('/api/auth/login', json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access_token')
    
    @task(3)
    def get_dashboard(self):
        """Get dashboard (high frequency)"""
        if self.token:
            headers = {'Authorization': f'Bearer {self.token}'}
            self.client.get('/api/student/dashboard', headers=headers)
    
    @task(2)
    def get_coding_questions(self):
        """Get coding questions"""
        if self.token:
            headers = {'Authorization': f'Bearer {self.token}'}
            self.client.get('/api/coding/questions', headers=headers)
    
    @task(1)
    def execute_code(self):
        """Execute code"""
        if self.token:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {
                'code': 'print("Hello, World!")',
                'language': 'python',
                'stdin': ''
            }
            self.client.post('/api/coding/execute', json=data, headers=headers)
    
    @task(1)
    def get_current_user(self):
        """Get current user info"""
        if self.token:
            headers = {'Authorization': f'Bearer {self.token}'}
            self.client.get('/api/auth/me', headers=headers)
    
    @task(1)
    def start_interview(self):
        """Start interview"""
        if self.token:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {
                'interview_type': 'technical',
                'resume_data': {},
                'jd_data': {}
            }
            self.client.post('/api/interview/start-interview', json=data, headers=headers)


class AuthUser(HttpUser):
    """Simulate authentication load"""
    wait_time = between(0.5, 2)
    
    @task(5)
    def login(self):
        """Test login endpoint"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        self.client.post('/api/auth/login', json=data)
    
    @task(1)
    def register(self):
        """Test registration endpoint"""
        data = {
            'username': f'loadtest_{random.randint(10000, 99999)}',
            'first_name': 'Load',
            'last_name': 'Test',
            'reg_no': f'LOAD{random.randint(10000, 99999)}',
            'college_email': f'loadtest_{random.randint(10000, 99999)}@audisankara.ac.in',
            'password': 'testpass123',
            'role': 'student'
        }
        self.client.post('/api/auth/register', json=data)
    
    @task(2)
    def get_auth_info(self):
        """Get auth info"""
        self.client.get('/api/auth/')


class CodingUser(HttpUser):
    """Simulate coding platform load"""
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login first"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post('/api/auth/login', json=data)
        if response.status_code == 200:
            self.token = response.json().get('access_token')
        else:
            self.token = None
    
    @task(3)
    def get_questions(self):
        """Get coding questions"""
        if self.token:
            headers = {'Authorization': f'Bearer {self.token}'}
            self.client.get('/api/coding/questions', headers=headers)
    
    @task(2)
    def execute_code(self):
        """Execute code"""
        if self.token:
            headers = {'Authorization': f'Bearer {self.token}'}
            code_samples = [
                'print("Hello")',
                'def add(a, b): return a + b',
                'x = [1, 2, 3]\nprint(sum(x))'
            ]
            data = {
                'code': random.choice(code_samples),
                'language': 'python',
                'stdin': ''
            }
            self.client.post('/api/coding/execute', json=data, headers=headers)
    
    @task(1)
    def submit_code(self):
        """Submit code"""
        if self.token:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {
                'question_id': random.randint(1, 10),
                'code': 'def solution(): return 42',
                'language': 'python'
            }
            self.client.post('/api/coding/submit', json=data, headers=headers)
