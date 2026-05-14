"""
Security Utilities - Production-Grade Security Features
JWT Refresh Tokens, Redis Rate Limiting, API Throttling, Audit Logs, Monitoring, Attack Protection
"""
import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
import logging
from logging.handlers import RotatingFileHandler
import os

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[Security] Redis not available. Install: pip install redis")

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)
audit_handler = RotatingFileHandler(
    os.path.join(log_dir, 'audit.log'),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5
)
audit_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
audit_logger.addHandler(audit_handler)

security_logger = logging.getLogger('security')
security_logger.setLevel(logging.WARNING)
security_handler = RotatingFileHandler(
    os.path.join(log_dir, 'security.log'),
    maxBytes=10 * 1024 * 1024,
    backupCount=5
)
security_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
security_logger.addHandler(security_handler)

# Redis client (initialized on first use)
_redis_client = None
_redis_checked = False

def get_redis_client():
    """Get or create Redis client"""
    global _redis_client, _redis_checked
    
    if not REDIS_AVAILABLE:
        return None
    
    if _redis_checked:
        return _redis_client
    
    if _redis_client is None:
        try:
            from config import Config
            
            if hasattr(Config, 'REDIS_URL') and Config.REDIS_URL:
                _redis_client = redis.from_url(
                    Config.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1
                )
                _redis_client.ping()
                print("[Security] Redis connected for rate limiting and brute force protection")
            else:
                _redis_client = None
        except Exception as e:
            print(f"[Security] Redis not available, using in-memory fallback: {e}")
            _redis_client = None
        finally:
            _redis_checked = True
    
    return _redis_client

# Fallback in-memory stores (used if Redis unavailable)
_rate_limit_store = {}
_brute_force_store = {}
_audit_logs = []


class TokenRefreshManager:
    """
    JWT Token Refresh Manager
    Handles access token and refresh token generation/validation
    """
    
    @staticmethod
    def create_tokens(user_id: int, additional_claims: Dict = None) -> Dict:
        """
        Create access token and refresh token
        
        Returns:
        {
            'access_token': str,
            'refresh_token': str,
            'expires_in': int (seconds)
        }
        """
        # Create access token (short-lived: 1 hour)
        access_token = create_access_token(
            identity=str(user_id),
            additional_claims=additional_claims or {},
            expires_delta=timedelta(hours=1)
        )
        
        # Create refresh token (long-lived: 30 days)
        refresh_token = create_refresh_token(
            identity=str(user_id),
            expires_delta=timedelta(days=30)
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': 3600,  # 1 hour in seconds
            'token_type': 'Bearer'
        }
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[Dict]:
        """
        Refresh access token using refresh token
        
        Returns new access token or None if invalid
        """
        try:
            # Decode refresh token
            decoded = decode_token(refresh_token)
            user_id = decoded.get('sub')
            
            if not user_id:
                return None
            
            # Create new access token
            access_token = create_access_token(
                identity=str(user_id),
                expires_delta=timedelta(hours=1)
            )
            
            return {
                'access_token': access_token,
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
        except Exception as e:
            security_logger.warning(f"Token refresh failed: {e}")
            return None


class RedisRateLimiter:
    """
    Redis-based Rate Limiter
    Uses Redis for distributed rate limiting across multiple instances
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_client = get_redis_client()
    
    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """
        Check if request is allowed using Redis sliding window
        
        Returns:
        (is_allowed: bool, remaining: int)
        """
        if not self.redis_client:
            # Fallback to in-memory
            return self._is_allowed_memory(identifier)
        
        try:
            key = f"rate_limit:{identifier}"
            now = time.time()
            
            # Use Redis sorted set for sliding window
            pipe = self.redis_client.pipeline()
            
            # Remove old entries (outside window)
            pipe.zremrangebyscore(key, 0, now - self.window_seconds)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiration
            pipe.expire(key, self.window_seconds)
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count >= self.max_requests:
                return False, 0
            
            remaining = self.max_requests - current_count - 1
            return True, max(0, remaining)
            
        except Exception as e:
            security_logger.warning(f"Redis rate limit error, falling back to memory: {e}")
            return self._is_allowed_memory(identifier)
    
    def _is_allowed_memory(self, identifier: str) -> tuple[bool, int]:
        """Fallback in-memory rate limiting"""
        now = time.time()
        key = identifier
        
        if key not in _rate_limit_store:
            _rate_limit_store[key] = []
        
        # Clean old entries
        _rate_limit_store[key] = [
            timestamp for timestamp in _rate_limit_store[key]
            if now - timestamp < self.window_seconds
        ]
        
        # Check limit
        if len(_rate_limit_store[key]) >= self.max_requests:
            return False, 0
        
        # Add current request
        _rate_limit_store[key].append(now)
        
        remaining = self.max_requests - len(_rate_limit_store[key])
        return True, remaining


class RedisBruteForceProtection:
    """
    Redis-based Brute Force Attack Protection
    Tracks failed login attempts and locks accounts using Redis
    """
    
    def __init__(self, max_attempts: int = 5, lockout_duration: int = 900):  # 15 minutes
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        self.redis_client = get_redis_client()
    
    def record_failed_attempt(self, identifier: str) -> bool:
        """
        Record failed login attempt
        
        Returns True if account should be locked
        """
        if not self.redis_client:
            return self._record_failed_attempt_memory(identifier)
        
        try:
            key = f"brute_force:{identifier}"
            now = time.time()
            
            # Get current attempts
            attempts = self.redis_client.incr(key)
            
            # Set expiration on first attempt
            if attempts == 1:
                self.redis_client.expire(key, self.lockout_duration)
            
            # Check if should lock
            if attempts >= self.max_attempts:
                lock_key = f"brute_force_lock:{identifier}"
                self.redis_client.setex(lock_key, self.lockout_duration, str(now))
                security_logger.warning(
                    f"Brute force protection: Locked {identifier} for {self.lockout_duration} seconds"
                )
                return True
            
            return False
            
        except Exception as e:
            security_logger.warning(f"Redis brute force error, falling back to memory: {e}")
            return self._record_failed_attempt_memory(identifier)
    
    def _record_failed_attempt_memory(self, identifier: str) -> bool:
        """Fallback in-memory brute force protection"""
        now = time.time()
        
        if identifier not in _brute_force_store:
            _brute_force_store[identifier] = {'attempts': 0, 'locked_until': None}
        
        record = _brute_force_store[identifier]
        
        # Check if already locked
        if record['locked_until'] and now < record['locked_until']:
            return True
        
        # Reset if lockout expired
        if record['locked_until'] and now >= record['locked_until']:
            record['attempts'] = 0
            record['locked_until'] = None
        
        # Increment attempts
        record['attempts'] += 1
        
        # Lock if exceeded max attempts
        if record['attempts'] >= self.max_attempts:
            record['locked_until'] = now + self.lockout_duration
            security_logger.warning(
                f"Brute force protection: Locked {identifier} for {self.lockout_duration} seconds"
            )
            return True
        
        return False
    
    def record_success(self, identifier: str):
        """Reset failed attempts on successful login"""
        if self.redis_client:
            try:
                self.redis_client.delete(f"brute_force:{identifier}")
                self.redis_client.delete(f"brute_force_lock:{identifier}")
            except Exception as e:
                security_logger.warning(f"Redis clear attempts error: {e}")
        else:
            if identifier in _brute_force_store:
                _brute_force_store[identifier] = {'attempts': 0, 'locked_until': None}
    
    def is_locked(self, identifier: str) -> tuple[bool, Optional[int]]:
        """
        Check if identifier is locked
        
        Returns:
        (is_locked: bool, remaining_seconds: Optional[int])
        """
        if self.redis_client:
            try:
                lock_key = f"brute_force_lock:{identifier}"
                ttl = self.redis_client.ttl(lock_key)
                
                if ttl > 0:
                    return True, ttl
                elif ttl == -2:  # Key doesn't exist
                    return False, None
                else:
                    return False, None
            except Exception as e:
                security_logger.warning(f"Redis lock check error: {e}")
                return False, None
        else:
            # Fallback to memory
            record = _brute_force_store.get(identifier, {'attempts': 0, 'locked_until': None})
            
            if not record['locked_until']:
                return False, None
            
            now = time.time()
            if now >= record['locked_until']:
                record['attempts'] = 0
                record['locked_until'] = None
                return False, None
            
            remaining = int(record['locked_until'] - now)
            return True, remaining
    
    def get_remaining_attempts(self, identifier: str) -> int:
        """Get remaining login attempts before lockout"""
        if self.redis_client:
            try:
                key = f"brute_force:{identifier}"
                attempts = int(self.redis_client.get(key) or 0)
                return max(0, self.max_attempts - attempts)
            except Exception as e:
                security_logger.warning(f"Redis get attempts error: {e}")
                return self.max_attempts
        else:
            record = _brute_force_store.get(identifier, {'attempts': 0, 'locked_until': None})
            return max(0, self.max_attempts - record['attempts'])


class APIThrottler:
    """
    API Throttling - More granular than rate limiting
    Different limits for different endpoints
    Uses Redis for distributed throttling
    """
    
    def __init__(self):
        self.endpoint_limits = {
            '/api/auth/login': {'max': 5, 'window': 60},  # 5 per minute
            '/api/auth/register': {'max': 3, 'window': 300},  # 3 per 5 minutes
            '/api/interview/start-interview': {'max': 10, 'window': 3600},  # 10 per hour
            '/api/coding/submit': {'max': 50, 'window': 60},  # 50 per minute
            'default': {'max': 100, 'window': 60},  # Default: 100 per minute
        }
        self.redis_client = get_redis_client()
    
    def is_allowed(self, endpoint: str, identifier: str) -> tuple[bool, int, Optional[int]]:
        """
        Check if request is allowed for specific endpoint
        
        Returns:
        (is_allowed: bool, remaining: int, retry_after: Optional[int] seconds)
        """
        limit_config = self.endpoint_limits.get(endpoint) or self.endpoint_limits['default']
        max_requests = limit_config['max']
        window_seconds = limit_config['window']
        
        if self.redis_client:
            try:
                key = f"throttle:{endpoint}:{identifier}"
                now = time.time()
                
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, window_seconds)
                
                results = pipe.execute()
                current_count = results[1]
                
                if current_count >= max_requests:
                    # Get oldest request to calculate retry_after
                    oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        oldest_time = oldest[0][1]
                        retry_after = int(window_seconds - (now - oldest_time)) + 1
                        return False, 0, retry_after
                    return False, 0, window_seconds
                
                remaining = max_requests - current_count - 1
                return True, max(0, remaining), None
                
            except Exception as e:
                security_logger.warning(f"Redis throttle error: {e}")
                # Fallback to memory
                pass
        
        # Fallback to memory
        now = time.time()
        key = f"{endpoint}:{identifier}"
        
        if key not in _rate_limit_store:
            _rate_limit_store[key] = []
        
        _rate_limit_store[key] = [
            timestamp for timestamp in _rate_limit_store[key]
            if now - timestamp < window_seconds
        ]
        
        if len(_rate_limit_store[key]) >= max_requests:
            oldest_request = min(_rate_limit_store[key])
            retry_after = int(window_seconds - (now - oldest_request)) + 1
            return False, 0, retry_after
        
        _rate_limit_store[key].append(now)
        remaining = max_requests - len(_rate_limit_store[key])
        return True, remaining, None


class AuditLogger:
    """
    Audit Logging - Track all user actions for security and compliance
    Logs to file and optionally to Redis for distributed systems
    """
    
    @staticmethod
    def log_action(
        user_id: Optional[int],
        action: str,
        resource: str,
        status: str = 'success',
        details: Dict = None,
        ip_address: str = None
    ):
        """
        Log user action for audit trail
        
        Args:
            user_id: User ID (None for anonymous)
            action: Action performed (login, logout, create, update, delete, etc.)
            resource: Resource affected (user, question, interview, etc.)
            status: success, failure, error
            details: Additional details
            ip_address: Client IP address
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'status': status,
            'ip_address': ip_address or request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'endpoint': request.endpoint or request.path,
            'method': request.method,
            'details': details or {},
        }
        
        # Log to file
        audit_logger.info(json.dumps(log_entry))
        
        # Also store in Redis for distributed systems (optional)
        redis_client = get_redis_client()
        if redis_client:
            try:
                # Store last 1000 audit logs in Redis (for quick access)
                redis_key = f"audit_log:{user_id or 'anonymous'}"
                redis_client.lpush(redis_key, json.dumps(log_entry))
                redis_client.ltrim(redis_key, 0, 999)  # Keep only last 1000
                redis_client.expire(redis_key, 86400 * 7)  # 7 days
            except Exception as e:
                security_logger.warning(f"Redis audit log error: {e}")
        
        # Keep in memory for quick access (last 1000)
        _audit_logs.append(log_entry)
        if len(_audit_logs) > 1000:
            _audit_logs.pop(0)
    
    @staticmethod
    def get_audit_logs(user_id: Optional[int] = None, limit: int = 100) -> List[Dict]:
        """Get audit logs (filtered by user_id if provided)"""
        redis_client = get_redis_client()
        
        if redis_client and user_id:
            try:
                redis_key = f"audit_log:{user_id}"
                logs_json = redis_client.lrange(redis_key, 0, limit - 1)
                return [json.loads(log) for log in logs_json]
            except Exception as e:
                security_logger.warning(f"Redis get audit logs error: {e}")
        
        # Fallback to memory
        logs = _audit_logs
        if user_id:
            logs = [log for log in logs if log.get('user_id') == user_id]
        return logs[-limit:]


class AttackProtection:
    """
    Attack Protection - Detect and prevent common attacks
    """
    
    @staticmethod
    def detect_sql_injection(input_str: str) -> bool:
        """Detect SQL injection patterns"""
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"('|(\\')|(;)|(\\;)|(--)|(\\--))",
        ]
        import re
        for pattern in sql_patterns:
            if re.search(pattern, input_str, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def detect_xss(input_str: str) -> bool:
        """Detect XSS patterns"""
        xss_patterns = [
            r"<script",
            r"javascript:",
            r"onerror=",
            r"onload=",
            r"onclick=",
            r"<iframe",
            r"<img.*onerror",
        ]
        import re
        for pattern in xss_patterns:
            if re.search(pattern, input_str, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def sanitize_input(input_str: str) -> str:
        """Sanitize user input"""
        import html
        # HTML escape
        sanitized = html.escape(input_str)
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        return sanitized


# Global instances
_brute_force_protection = RedisBruteForceProtection()
_rate_limiter = RedisRateLimiter()

# Decorators for easy use
def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """Decorator for rate limiting"""
    limiter = RedisRateLimiter(max_requests, window_seconds)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = get_client_identifier()
            is_allowed, remaining = limiter.is_allowed(identifier)
            
            if not is_allowed:
                AuditLogger.log_action(
                    user_id=None,
                    action='rate_limit_exceeded',
                    resource=request.endpoint,
                    status='failure',
                    ip_address=request.remote_addr
                )
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': window_seconds
                }), 429
            
            # Add remaining count to response headers
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                response.headers['X-RateLimit-Reset'] = str(int(time.time()) + window_seconds)
            
            return response
        return decorated_function
    return decorator


def throttle_endpoint(endpoint: str = None):
    """Decorator for endpoint-specific throttling"""
    throttler = APIThrottler()
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ep = endpoint or request.endpoint
            identifier = get_client_identifier()
            is_allowed, remaining, retry_after = throttler.is_allowed(ep, identifier)
            
            if not is_allowed:
                AuditLogger.log_action(
                    user_id=None,
                    action='throttle_exceeded',
                    resource=ep,
                    status='failure',
                    ip_address=request.remote_addr
                )
                return jsonify({
                    'error': 'API throttle exceeded',
                    'retry_after': retry_after
                }), 429
            
            response = f(*args, **kwargs)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Remaining'] = str(remaining)
                if retry_after:
                    response.headers['X-RateLimit-Reset'] = str(int(time.time()) + retry_after)
            
            return response
        return decorated_function
    return decorator


def audit_log(action: str, resource: str):
    """Decorator for audit logging"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_jwt_extended import get_jwt_identity
            user_id = get_jwt_identity() if hasattr(request, 'jwt') else None
            
            try:
                response = f(*args, **kwargs)
                status = 'success' if (hasattr(response, '__len__') and len(response) > 1 and response[1] < 400) or (not hasattr(response, '__len__')) else 'failure'
                AuditLogger.log_action(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    status=status,
                    ip_address=request.remote_addr
                )
                return response
            except Exception as e:
                AuditLogger.log_action(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    status='error',
                    details={'error': str(e)},
                    ip_address=request.remote_addr
                )
                raise
        return decorated_function
    return decorator


def protect_against_attacks(f):
    """Decorator to protect against common attacks"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check request data for attacks
        if request.is_json:
            data = request.get_json()
            for key, value in data.items():
                if isinstance(value, str):
                    if AttackProtection.detect_sql_injection(value):
                        security_logger.warning(f"SQL injection attempt detected: {key}")
                        AuditLogger.log_action(
                            user_id=None,
                            action='sql_injection_attempt',
                            resource=request.endpoint,
                            status='blocked',
                            details={'field': key},
                            ip_address=request.remote_addr
                        )
                        return jsonify({'error': 'Invalid input detected'}), 400
                    if AttackProtection.detect_xss(value):
                        security_logger.warning(f"XSS attempt detected: {key}")
                        AuditLogger.log_action(
                            user_id=None,
                            action='xss_attempt',
                            resource=request.endpoint,
                            status='blocked',
                            details={'field': key},
                            ip_address=request.remote_addr
                        )
                        return jsonify({'error': 'Invalid input detected'}), 400
        
        return f(*args, **kwargs)
    return decorated_function


def get_client_identifier() -> str:
    """Get client identifier for rate limiting and brute force protection"""
    # Try to get user ID from JWT
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}"
    except:
        pass
    
    # Fallback to IP address
    return f"ip:{request.remote_addr or 'unknown'}"


def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response


# Export for backward compatibility
BruteForceProtection = RedisBruteForceProtection
RateLimiter = RedisRateLimiter
