"""
Async Processing Utilities for CV & AI
Handles background processing, retry logic, and caching
"""
import threading
import time
import functools
import hashlib
import json
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
import requests
from config import Config

# Simple in-memory cache (for production, use Redis)
_cache = {}
_cache_ttl = {}  # Time-to-live for cache entries

# Background task queue
_task_queue = []
_task_results = {}
_task_lock = threading.Lock()

def get_cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
    return hashlib.md5(key_data.encode()).hexdigest()

def cache_result(ttl_seconds: int = 3600):
    """
    Decorator to cache function results
    Args:
        ttl_seconds: Time-to-live in seconds (default: 1 hour)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{get_cache_key(*args, **kwargs)}"
            
            # Check cache
            if cache_key in _cache:
                cache_time = _cache_ttl.get(cache_key, 0)
                if time.time() < cache_time:
                    return _cache[cache_key]
                else:
                    # Cache expired
                    del _cache[cache_key]
                    del _cache_ttl[cache_key]
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            _cache[cache_key] = result
            _cache_ttl[cache_key] = time.time() + ttl_seconds
            
            return result
        return wrapper
    return decorator

def clear_cache(pattern: str = None):
    """Clear cache entries (optionally by pattern)"""
    global _cache, _cache_ttl
    if pattern:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for k in keys_to_delete:
            _cache.pop(k, None)
            _cache_ttl.pop(k, None)
    else:
        _cache.clear()
        _cache_ttl.clear()

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, 
                      backoff_factor: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Decorator for retry logic with exponential backoff
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"[Retry] {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        print(f"[Retry] Retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        print(f"[Retry] {func.__name__} failed after {max_retries + 1} attempts")
                        raise
            
            if last_exception:
                raise last_exception
        return wrapper
    return decorator

def run_in_background(func: Callable, *args, **kwargs) -> str:
    """
    Run function in background thread
    Returns task_id for tracking
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    def background_task():
        try:
            result = func(*args, **kwargs)
            with _task_lock:
                _task_results[task_id] = {
                    'status': 'completed',
                    'result': result,
                    'completed_at': datetime.utcnow().isoformat()
                }
        except Exception as e:
            with _task_lock:
                _task_results[task_id] = {
                    'status': 'failed',
                    'error': str(e),
                    'completed_at': datetime.utcnow().isoformat()
                }
    
    with _task_lock:
        _task_results[task_id] = {
            'status': 'pending',
            'started_at': datetime.utcnow().isoformat()
        }
    
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()
    
    return task_id

def get_task_status(task_id: str) -> Optional[Dict]:
    """Get status of background task"""
    with _task_lock:
        return _task_results.get(task_id)

def cleanup_old_tasks(max_age_hours: int = 24):
    """Clean up old task results"""
    cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
    with _task_lock:
        keys_to_delete = []
        for task_id, task_data in _task_results.items():
            completed_at_str = task_data.get('completed_at')
            if completed_at_str:
                try:
                    completed_at = datetime.fromisoformat(completed_at_str.replace('Z', '+00:00'))
                    if completed_at < cutoff_time:
                        keys_to_delete.append(task_id)
                except:
                    pass
        
        for key in keys_to_delete:
            _task_results.pop(key, None)

