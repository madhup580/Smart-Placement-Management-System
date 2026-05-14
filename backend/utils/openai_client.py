"""
OpenAI API Client with Retry Logic and Error Handling
"""
import requests
import time
import json
import re
from typing import Optional, Dict, List
from config import Config
from utils.async_utils import retry_with_backoff, cache_result

class OpenAIError(Exception):
    """Custom exception for OpenAI API errors"""
    pass

class OpenAIClient:
    """OpenAI API client with retry logic and error handling"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = None):
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.base_url = base_url or Config.AI_API_URL
        self.model = Config.OPENAI_MODEL
        self.max_retries = 3
        self.retry_delay = 1.0
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0, backoff_factor=2.0,
                        exceptions=(requests.exceptions.RequestException, OpenAIError))
    def _make_request(self, messages: List[Dict], max_tokens: int = 500, 
                     temperature: float = 0.7, timeout: int = 30) -> Dict:
        """
        Make OpenAI API request with retry logic
        """
        if not self.api_key:
            raise OpenAIError("OpenAI API key not configured")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"[OpenAI] Rate limited. Waiting {retry_after} seconds...")
                time.sleep(min(retry_after, 60))  # Cap at 60 seconds
                raise OpenAIError("Rate limit exceeded - retrying")
            
            # Handle other errors
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                
                # Check for quota errors
                if response.status_code == 429 or 'quota' in error_msg.lower():
                    raise OpenAIError(f"API quota exceeded: {error_msg}")
                
                # Check for authentication errors
                if response.status_code == 401:
                    raise OpenAIError(f"Invalid API key: {error_msg}")
                
                raise OpenAIError(f"API error ({response.status_code}): {error_msg}")
            
            return response.json()
            
        except requests.exceptions.Timeout:
            raise OpenAIError("Request timeout - API took too long to respond")
        except requests.exceptions.ConnectionError:
            raise OpenAIError("Connection error - unable to reach OpenAI API")
        except json.JSONDecodeError:
            raise OpenAIError("Invalid JSON response from API")
    
    def chat_completion(self, messages: List[Dict], max_tokens: int = 500, 
                       temperature: float = 0.7, timeout: int = 30) -> str:
        """
        Get chat completion from OpenAI
        Returns the content of the assistant's message
        """
        try:
            data = self._make_request(messages, max_tokens, temperature, timeout)
            
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0]['message']['content'].strip()
                return content
            else:
                raise OpenAIError("No response from OpenAI API")
                
        except OpenAIError:
            raise
        except Exception as e:
            raise OpenAIError(f"Unexpected error: {str(e)}")
    
    @cache_result(ttl_seconds=3600)  # Cache for 1 hour
    def chat_completion_cached(self, messages: List[Dict], max_tokens: int = 500, 
                              temperature: float = 0.7) -> str:
        """
        Cached version of chat_completion (caches based on messages)
        Note: Only use for deterministic requests
        """
        return self.chat_completion(messages, max_tokens, temperature)

# Global client instance
_openai_client = None

def get_openai_client() -> OpenAIClient:
    """Get or create OpenAI client instance"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client

