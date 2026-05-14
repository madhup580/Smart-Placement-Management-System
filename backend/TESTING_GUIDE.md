# Testing Guide

## 🧪 Complete Testing Infrastructure

This project now includes comprehensive testing with:
- ✅ **pytest** for unit tests
- ✅ **HTTPX** for API integration tests
- ✅ **Locust** for load/performance tests
- ✅ **GitHub Actions** for CI/CD

## 📦 Installation

```bash
# Install all test dependencies
cd backend
pip install -r requirements.txt

# Or use Makefile
make install-test
```

## 🚀 Quick Start

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Run Load Tests
```bash
# Start Flask app
python -m flask run

# In another terminal, run Locust
locust -f tests/load/locustfile.py --host=http://127.0.0.1:5000
```

## 📁 Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_auth.py             # Authentication unit tests
├── test_coding.py           # Coding endpoint unit tests
├── test_interview.py        # Interview endpoint unit tests
├── test_security.py         # Security feature unit tests
├── api/
│   └── test_api_integration.py  # HTTPX API integration tests
└── load/
    └── locustfile.py        # Locust load test scenarios
```

## 🧩 Test Types

### 1. Unit Tests (pytest)

Test individual components in isolation.

**Example:**
```python
def test_login_success(client, test_user):
    data = {'username': 'testuser', 'password': 'testpass123'}
    response = client.post('/api/auth/login', json=data)
    assert response.status_code == 200
    assert 'access_token' in response.json()
```

**Run:**
```bash
pytest tests/test_auth.py -v
```

### 2. API Integration Tests (HTTPX)

Test full API flow end-to-end.

**Example:**
```python
@pytest.mark.asyncio
async def test_api_flow(client):
    # Register
    response = await client.post('/api/auth/register', json=register_data)
    token = response.json()['access_token']
    
    # Use token
    headers = {'Authorization': f'Bearer {token}'}
    response = await client.get('/api/auth/me', headers=headers)
    assert response.status_code == 200
```

**Run:**
```bash
# Start Flask app first
python -m flask run

# Run API tests
pytest tests/api/ -v
```

### 3. Load Tests (Locust)

Test system performance under load.

**Example:**
```python
class APIUser(HttpUser):
    @task
    def get_dashboard(self):
        self.client.get('/api/dashboard')
```

**Run:**
```bash
# Web UI (recommended)
locust -f tests/load/locustfile.py --host=http://127.0.0.1:5000
# Open http://127.0.0.1:8089

# Headless mode
locust -f tests/load/locustfile.py --host=http://127.0.0.1:5000 \
  --headless -u 10 -r 2 -t 30s
```

## 🔧 Configuration Files

### pytest.ini
- Test discovery patterns
- Coverage settings
- Markers for test categorization

### .flake8
- Code linting rules
- Line length: 127
- Complexity: 10

### .coveragerc
- Coverage exclusions
- Report settings

### Makefile
- Convenient commands for common tasks

## 📊 Coverage Goals

- **Target**: >80% code coverage
- **Critical paths**: 100% coverage
- **View report**: `pytest --cov=. --cov-report=html`

## 🔄 CI/CD Pipeline

GitHub Actions automatically runs:
1. **Unit Tests** - All pytest tests
2. **API Tests** - HTTPX integration tests
3. **Linting** - flake8, black, isort
4. **Load Tests** - Locust performance tests

**Triggered on:**
- Push to main/develop
- Pull requests

## 📝 Writing Tests

### Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for common setup
3. **Naming**: Descriptive test names (`test_what_when_then`)
4. **Assertions**: Clear, specific assertions
5. **Coverage**: Test happy paths and edge cases

### Test Template

```python
def test_feature_scenario(client, test_user):
    """Test: Feature does X when Y"""
    # Arrange
    data = {...}
    
    # Act
    response = client.post('/api/endpoint', json=data)
    
    # Assert
    assert response.status_code == 200
    assert 'expected_field' in response.json()
```

## 🎯 Test Scenarios

### Authentication Tests
- ✅ Registration (success, duplicate, invalid)
- ✅ Login (success, invalid, brute force)
- ✅ Token refresh
- ✅ Current user endpoint
- ✅ Logout

### Security Tests
- ✅ Rate limiting
- ✅ Brute force protection
- ✅ SQL injection detection
- ✅ XSS detection
- ✅ Token refresh

### Coding Tests
- ✅ Get questions
- ✅ Execute code
- ✅ Submit code
- ✅ Unauthorized access

### Interview Tests
- ✅ Start interview
- ✅ Submit answer
- ✅ Session state

## 📈 Performance Benchmarks

Load tests measure:
- **Response time**: <200ms for most endpoints
- **Throughput**: >100 req/s
- **Error rate**: <1%

## 🐛 Troubleshooting

### Tests failing with database errors
```bash
# Ensure test database is configured
export SQLALCHEMY_DATABASE_URI=sqlite:///:memory:
```

### API tests timing out
```bash
# Ensure Flask app is running
python -m flask run

# Check BASE_URL in test file
```

### Load tests not working
```bash
# Ensure services are running
redis-server
mysql-server

# Check host in locustfile.py
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [HTTPX Documentation](https://www.python-httpx.org/)
- [Locust Documentation](https://docs.locust.io/)
- [GitHub Actions](https://docs.github.com/en/actions)

## ✅ Testing Checklist

- [ ] All unit tests passing
- [ ] API integration tests passing
- [ ] Load tests within performance targets
- [ ] Code coverage >80%
- [ ] No linting errors
- [ ] CI/CD pipeline green
