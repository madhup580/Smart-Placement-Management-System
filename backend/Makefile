.PHONY: test test-unit test-api test-load test-cov lint format clean

# Run all tests
test:
	pytest

# Run unit tests only
test-unit:
	pytest tests/ -k "not api and not load"

# Run API integration tests
test-api:
	pytest tests/api/ -v

# Run load tests
test-load:
	locust -f tests/load/locustfile.py --host=http://localhost:5000

# Run tests with coverage
test-cov:
	pytest --cov=. --cov-report=html --cov-report=term

# Lint code
lint:
	flake8 .
	black --check .
	isort --check-only .

# Format code
format:
	black .
	isort .

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf load_test_report.html
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

# Install test dependencies
install-test:
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov httpx locust flake8 black isort
