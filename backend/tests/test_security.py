"""
Unit tests for security features
"""
import pytest
from utils.security import (
    TokenRefreshManager,
    RedisRateLimiter,
    RedisBruteForceProtection,
    AuditLogger,
    AttackProtection
)


class TestTokenRefreshManager:
    """Test token refresh manager"""
    
    def test_create_tokens(self, app, test_user):
        """Test token creation"""
        with app.app_context():
            tokens = TokenRefreshManager.create_tokens(test_user.id)
            
            assert 'access_token' in tokens
            assert 'refresh_token' in tokens
            assert 'expires_in' in tokens
            assert tokens['expires_in'] == 3600
            assert tokens['token_type'] == 'Bearer'


class TestRateLimiter:
    """Test rate limiter"""
    
    def test_rate_limit_allowed(self):
        """Test rate limit allows requests within limit"""
        limiter = RedisRateLimiter(max_requests=10, window_seconds=60)
        identifier = 'test_ip'
        
        # Make 5 requests
        for i in range(5):
            is_allowed, remaining = limiter.is_allowed(identifier)
            assert is_allowed is True
            assert remaining >= 0
    
    def test_rate_limit_exceeded(self):
        """Test rate limit blocks requests over limit"""
        limiter = RedisRateLimiter(max_requests=3, window_seconds=60)
        identifier = 'test_ip'
        
        # Make 3 requests (should all pass)
        for i in range(3):
            is_allowed, remaining = limiter.is_allowed(identifier)
            assert is_allowed is True
        
        # 4th request should be blocked
        is_allowed, remaining = limiter.is_allowed(identifier)
        assert is_allowed is False
        assert remaining == 0


class TestBruteForceProtection:
    """Test brute force protection"""
    
    def test_brute_force_protection(self):
        """Test brute force protection locks after max attempts"""
        protection = RedisBruteForceProtection(max_attempts=3, lockout_duration=60)
        identifier = 'test_ip'
        
        # Make 2 failed attempts
        for i in range(2):
            is_locked = protection.record_failed_attempt(identifier)
            assert is_locked is False
        
        # 3rd attempt should lock
        is_locked = protection.record_failed_attempt(identifier)
        assert is_locked is True
        
        # Check if locked
        is_locked, remaining = protection.is_locked(identifier)
        assert is_locked is True
    
    def test_brute_force_reset_on_success(self):
        """Test brute force protection resets on successful login"""
        protection = RedisBruteForceProtection(max_attempts=3, lockout_duration=60)
        identifier = 'test_ip'
        
        # Make 2 failed attempts
        protection.record_failed_attempt(identifier)
        protection.record_failed_attempt(identifier)
        
        # Record success
        protection.record_success(identifier)
        
        # Should not be locked
        is_locked, remaining = protection.is_locked(identifier)
        assert is_locked is False


class TestAttackProtection:
    """Test attack protection"""
    
    def test_sql_injection_detection(self):
        """Test SQL injection detection"""
        malicious_input = "'; DROP TABLE users; --"
        assert AttackProtection.detect_sql_injection(malicious_input) is True
    
    def test_xss_detection(self):
        """Test XSS detection"""
        malicious_input = "<script>alert('XSS')</script>"
        assert AttackProtection.detect_xss(malicious_input) is True
    
    def test_sanitize_input(self):
        """Test input sanitization"""
        malicious_input = "<script>alert('XSS')</script>"
        sanitized = AttackProtection.sanitize_input(malicious_input)
        assert '<script>' not in sanitized


class TestAuditLogger:
    """Test audit logger"""
    
    def test_audit_log_action(self):
        """Test audit logging"""
        # This should not raise an exception
        AuditLogger.log_action(
            user_id=1,
            action='test',
            resource='test_resource',
            status='success',
            details={'test': 'data'}
        )
