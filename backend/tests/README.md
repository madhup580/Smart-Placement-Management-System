# Testing Documentation

## Overview

This project includes comprehensive testing infrastructure:
- **Unit Tests**: pytest for testing individual components
- **API Tests**: HTTPX for end-to-end API testing
- **Load Tests**: Locust for performance testing
- **CI/CD**: GitHub Actions for automated testing

## Running Tests

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::TestAuth::test_login_success

# Run with verbose output
pytest -v

# Run only fast tests (exclude slow)
pytest -m "not slow"
```

### API Integration Tests

```bash
# Start Flask app first
python -m flask run

# In another terminal, run API tests
pytest tests/api/ -v
```

### Load Tests

```bash
# Install locust
pip install locust

# Start Flask app
python -m flask run

# Run load tests (web UI)
locust -f tests/load/locustfile.py --host=http://localhost:5000

# Run load tests (headless)
locust -f tests/load/locustfile.py --host=http://localhost:5000 --headless -u 10 -r 2 -t 30s
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_auth.py             # Authentication tests
├── test_coding.py           # Coding endpoint tests
├── test_interview.py        # Interview endpoint tests
├── test_security.py         # Security feature tests
├── api/
│   └── test_api_integration.py  # API integration tests
└── load/
    └── locustfile.py        # Load test scenarios
```

## Test Coverage

Current coverage targets:
- **Unit Tests**: >80% coverage
- **API Tests**: All critical endpoints
- **Load Tests**: Performance benchmarks

View coverage report:
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Writing Tests

### Unit Test Example

```python
def test_login_success(client, test_user):
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
    data = response.json()
    assert 'access_token' in data
```

### API Test Example

```python
@pytest.mark.asyncio
async def test_api_endpoint(client):
    """Test API endpoint"""
    response = await client.get('/api/endpoint')
    assert response.status_code == 200
```

### Load Test Example

```python
class APIUser(HttpUser):
    @task
    def get_dashboard(self):
        self.client.get('/api/dashboard')
```

## CI/CD

Tests run automatically on:
- Push to main/develop branches
- Pull requests

CI pipeline includes:
1. Unit tests with coverage
2. API integration tests
3. Code linting (flake8, black, isort)
4. Load tests

## Test Data

- Test users are created automatically via fixtures
- Database is reset between tests
- Redis is disabled for unit tests (in-memory fallback)

## Best Practices

1. **Isolation**: Each test should be independent
2. **Fixtures**: Use fixtures for common setup
3. **Assertions**: Clear, specific assertions
4. **Naming**: Descriptive test names
5. **Coverage**: Aim for >80% code coverage
6. **Speed**: Keep tests fast (<1s per test)

## Troubleshooting

### Tests failing with database errors
- Ensure test database is properly configured
- Check that fixtures are creating test data correctly

### API tests timing out
- Ensure Flask app is running
- Check that BASE_URL is correct

### Load tests not working
- Ensure Flask app is running
- Check that Redis/MySQL are available
- Increase timeout if needed
