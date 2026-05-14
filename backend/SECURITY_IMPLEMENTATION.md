# Security Improvements Implementation

## Overview
This document describes the security improvements added to the platform:
1. Token Refresh Mechanism
2. API Rate Limiting
3. Brute Force Login Protection
4. CSRF Token Protection
5. API Versioning

## 1. Token Refresh Mechanism

### Backend
- **Access Token**: 1 hour expiry (reduced from 24 hours for better security)
- **Refresh Token**: 30 days expiry
- **Endpoint**: `POST /api/auth/refresh` (requires refresh token)
- **Rate Limited**: 10 refreshes per minute per user

### Frontend
- **Auto-refresh**: Token manager automatically refreshes tokens when < 5 minutes remaining
- **Intercept 401**: Automatically retries requests with refreshed token
- **Multi-tab support**: Tokens synchronized across browser tabs

### Usage
```javascript
// Tokens are automatically managed
// Access token is refreshed before expiry
// 401 responses trigger automatic refresh and retry
```

## 2. API Rate Limiting

### Global Limits
- **Default**: 200 requests per day, 50 per hour per IP
- **Storage**: In-memory (development), Redis (production)

### Route-Specific Limits
- **Login**: 10 attempts per 15 minutes per IP
- **Register**: 5 registrations per hour per IP
- **Token Refresh**: 10 refreshes per minute per user

### Response Headers
Rate limit info included in response headers:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Time when limit resets
- `Retry-After`: Seconds to wait before retry (on 429)

### Error Response
```json
{
    "error": "Rate limit exceeded",
    "retry_after": 60
}
```

## 3. Brute Force Login Protection

### Protection Mechanism
- **Max Attempts**: 5 failed attempts
- **Lockout Duration**: 15 minutes
- **Window**: 5 minutes rolling window
- **Tracking**: Per IP address (or username+IP)

### Behavior
1. Failed login → Record attempt
2. 5 failed attempts → Lockout for 15 minutes
3. Successful login → Clear attempts
4. Lockout expired → Automatic unlock

### Error Response
```json
{
    "error": "Too many failed login attempts. Account temporarily locked.",
    "lockout_remaining": 900,
    "message": "Please try again in 15 minutes"
}
```

### Remaining Attempts
```json
{
    "error": "Invalid credentials",
    "remaining_attempts": 3
}
```

## 4. CSRF Token Protection

### Backend
- **Library**: Flask-WTF
- **Enabled**: For all POST/PUT/DELETE requests
- **Token Endpoint**: `GET /api/csrf-token`
- **Header**: `X-CSRF-Token`

### Frontend
- **Token Retrieval**: Fetch from `/api/csrf-token` before form submission
- **Header Inclusion**: Add `X-CSRF-Token` header to all state-changing requests

### Usage
```javascript
// Get CSRF token
const response = await fetch('/api/csrf-token');
const { csrf_token } = await response.json();

// Include in request
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRF-Token': csrf_token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```

## 5. API Versioning

### Version Structure
- **Current Version**: `/api/v1/`
- **Backward Compatibility**: Unversioned routes still work (`/api/`)

### Versioned Endpoints
All blueprints registered with both:
- `/api/v1/{resource}` (versioned)
- `/api/{resource}` (unversioned, for backward compatibility)

### Migration Path
1. **Phase 1**: Both versions available (current)
2. **Phase 2**: Deprecate unversioned, add warnings
3. **Phase 3**: Remove unversioned routes

## Security Headers

All responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'`

## Configuration

### Environment Variables
```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600  # 1 hour in seconds
JWT_REFRESH_TOKEN_EXPIRES=2592000  # 30 days in seconds

# CSRF Configuration
SECRET_KEY=your-secret-key-for-csrf
WTF_CSRF_ENABLED=True
WTF_CSRF_TIME_LIMIT=3600  # 1 hour

# Rate Limiting (Production)
RATE_LIMIT_STORAGE_URI=redis://localhost:6379
```

## Testing

### Rate Limiting
```bash
# Test rate limit
for i in {1..11}; do
    curl -X POST http://localhost:5000/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"test"}'
done
# 11th request should return 429
```

### Brute Force Protection
```bash
# Test brute force protection
for i in {1..6}; do
    curl -X POST http://localhost:5000/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"wrong"}'
done
# 6th request should return 429 with lockout
```

### Token Refresh
```bash
# Get refresh token from login
REFRESH_TOKEN="your-refresh-token"

# Refresh access token
curl -X POST http://localhost:5000/api/auth/refresh \
    -H "Authorization: Bearer $REFRESH_TOKEN"
```

## Production Recommendations

1. **Use Redis** for rate limiting storage (shared across instances)
2. **Use Redis** for brute force protection (shared tracking)
3. **Enable HTTPS** and update HSTS headers
4. **Rotate JWT secrets** regularly
5. **Monitor** rate limit breaches and brute force attempts
6. **Set up alerts** for suspicious activity
7. **Use environment variables** for all secrets
8. **Enable CSRF** for all state-changing operations

## Files Modified

- `backend/utils/security.py` - Security utilities
- `backend/routes/auth.py` - Enhanced with brute force protection
- `backend/app.py` - Rate limiting, CSRF, security headers
- `backend/config.py` - Security configuration
- `backend/requirements.txt` - Added Flask-Limiter, Flask-WTF
- `frontend/js/token_manager.js` - Auto-refresh mechanism
- `frontend/js/api.js` - Integrated token manager
