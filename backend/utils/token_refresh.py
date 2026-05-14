"""
Token Refresh Utilities
Auto-refresh mechanism for JWT tokens
"""
from flask_jwt_extended import decode_token, create_access_token
from datetime import datetime, timedelta
import jwt

def should_refresh_token(access_token):
    """
    Check if token should be refreshed (within 5 minutes of expiry)
    Returns: (should_refresh: bool, time_until_expiry: int seconds)
    """
    try:
        decoded = decode_token(access_token)
        exp = decoded.get('exp', 0)
        now = datetime.utcnow().timestamp()
        
        time_until_expiry = exp - now
        
        # Refresh if less than 5 minutes remaining
        should_refresh = time_until_expiry < 300  # 5 minutes
        
        return should_refresh, int(time_until_expiry)
    except Exception as e:
        # If token is invalid, should refresh
        return True, 0

def get_token_expiry(access_token):
    """Get token expiry timestamp"""
    try:
        decoded = decode_token(access_token)
        return decoded.get('exp', 0)
    except:
        return 0
