# Security Upgrade - Production-Ready Implementation

## ✅ Completed Upgrades

### 1. JWT + Refresh Token System
- **TokenRefreshManager**: Centralized token management
- **Access Token**: Short-lived (1 hour) for API requests
- **Refresh Token**: Long-lived (30 days) for token renewal
- **Auto-refresh**: Frontend automatically refreshes expired tokens
- **Secure Storage**: Tokens stored in httpOnly cookies (recommended) or localStorage

### 2. Redis Rate Limiting
- **RedisRateLimiter**: Distributed rate limiting using Redis
- **Sliding Window**: Accurate rate limiting with Redis sorted sets
- **Fallback**: In-memory fallback if Redis unavailable
- **Per-endpoint Limits**: Different limits for different endpoints
- **Headers**: Rate limit info included in response headers

### 3. Redis Brute Force Protection
- **RedisBruteForceProtection**: Distributed brute force protection
- **Lockout System**: Automatic account lockout after failed attempts
- **Configurable**: Max attempts (5) and lockout duration (15 minutes)
- **Per-identifier**: Tracks by IP or user ID
- **Auto-unlock**: Automatic unlock after lockout period

### 4. Audit Logging
- **AuditLogger**: Comprehensive audit trail
- **File Logging**: Rotating file logs (10MB, 5 backups)
- **Redis Storage**: Last 1000 logs stored in Redis for quick access
- **Log Fields**: timestamp, user_id, action, resource, status, IP, user_agent, endpoint
- **Automatic**: All auth actions automatically logged

### 5. Attack Protection
- **SQL Injection Detection**: Pattern-based detection
- **XSS Detection**: Script tag and event handler detection
- **Input Sanitization**: HTML escaping and null byte removal
- **Automatic Blocking**: Requests blocked if attack detected

## 🔧 Configuration

### Redis Setup

#### Option 1: Local Redis
```bash
# Install Redis
# Windows: Download from https://redis.io/download
# Mac: brew install redis
# Linux: sudo apt-get install redis-server

# Start Redis
redis-server

# Or using Docker
docker run -d -p 6379:6379 redis
```

#### Option 2: Redis Cloud
Set environment variable:
```bash
REDIS_URL=redis://username:password@host:port
```

#### Option 3: Fallback
If Redis is not available, the system automatically falls back to in-memory storage.

### Environment Variables
```bash
# Redis (optional - defaults to localhost:6379)
REDIS_URL=redis://localhost:6379

# JWT Secrets (required in production)
JWT_SECRET_KEY=your-secret-key-here
SECRET_KEY=your-secret-key-here
```

## 📊 Usage Examples

### Rate Limiting
```python
from utils.security import rate_limit

@route('/api/endpoint')
@rate_limit(max_requests=100, window_seconds=60)
def my_endpoint():
    return jsonify({'message': 'Success'})
```

### Brute Force Protection
```python
from utils.security import RedisBruteForceProtection

brute_force = RedisBruteForceProtection()
is_locked, remaining = brute_force.is_locked(identifier)
if is_locked:
    return jsonify({'error': 'Account locked'}), 429
```

### Audit Logging
```python
from utils.security import AuditLogger

AuditLogger.log_action(
    user_id=user.id,
    action='create',
    resource='question',
    status='success',
    details={'question_id': 123},
    ip_address=request.remote_addr
)
```

### Token Refresh
```python
from utils.security import TokenRefreshManager

token_manager = TokenRefreshManager()
tokens = token_manager.create_tokens(user_id)
# Returns: {'access_token': ..., 'refresh_token': ..., 'expires_in': 3600}
```

## 🔒 Security Features

1. **Token Security**
   - Short-lived access tokens (1 hour)
   - Long-lived refresh tokens (30 days)
   - Automatic token rotation
   - Secure token storage

2. **Rate Limiting**
   - Distributed rate limiting (Redis)
   - Per-endpoint limits
   - Sliding window algorithm
   - Automatic retry-after headers

3. **Brute Force Protection**
   - Automatic lockout after 5 failed attempts
   - 15-minute lockout duration
   - Per-IP and per-user tracking
   - Automatic unlock

4. **Audit Logging**
   - All auth actions logged
   - File-based logging (persistent)
   - Redis storage (quick access)
   - 7-day retention in Redis

5. **Attack Protection**
   - SQL injection detection
   - XSS detection
   - Input sanitization
   - Automatic request blocking

## 📈 Monitoring

### Audit Logs Location
- **File**: `backend/logs/audit.log`
- **Redis**: `audit_log:{user_id}` (last 1000 logs)

### Security Logs Location
- **File**: `backend/logs/security.log`

### Viewing Logs
```bash
# View audit logs
tail -f backend/logs/audit.log

# View security logs
tail -f backend/logs/security.log

# Query Redis audit logs
redis-cli
> LRANGE audit_log:123 0 99  # Last 100 logs for user 123
```

## 🚀 Production Checklist

- [ ] Set strong `JWT_SECRET_KEY` and `SECRET_KEY`
- [ ] Configure Redis URL (production Redis instance)
- [ ] Enable HTTPS (required for secure token transmission)
- [ ] Set up log rotation and monitoring
- [ ] Configure Redis persistence (AOF or RDB)
- [ ] Set up Redis backup strategy
- [ ] Monitor rate limit metrics
- [ ] Review audit logs regularly
- [ ] Set up alerts for security events

## 🔍 Testing

### Test Rate Limiting
```bash
# Make 100 requests quickly
for i in {1..100}; do curl http://localhost:5000/api/endpoint; done
# Should return 429 after limit exceeded
```

### Test Brute Force Protection
```bash
# Make 5 failed login attempts
for i in {1..5}; do curl -X POST http://localhost:5000/api/auth/login -d '{"username":"test","password":"wrong"}'; done
# 6th attempt should be blocked
```

### Test Token Refresh
```bash
# Get refresh token from login
REFRESH_TOKEN="your-refresh-token"

# Refresh access token
curl -X POST http://localhost:5000/api/auth/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN" \
  -d '{"refresh_token": "$REFRESH_TOKEN"}'
```

## 📝 Notes

- All security features have automatic fallbacks if Redis is unavailable
- Audit logs are always written to files (even without Redis)
- Rate limiting works in-memory if Redis unavailable (per-instance)
- Brute force protection works in-memory if Redis unavailable (per-instance)
- For production, Redis is **highly recommended** for distributed systems
