"""
Configuration settings for the Interview Preparation Platform
"""
import os
from datetime import timedelta

def _get_database_url():
    """Get database URL with proper formatting and fallback"""
    # Method 1: Try DATABASE_URL environment variable
    database_url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
    if database_url and not database_url.startswith('mysql+pymysql://'):
        # Convert mysql:// to mysql+pymysql:// if needed
        database_url = database_url.replace('mysql://', 'mysql+pymysql://', 1)
    if database_url:
        return database_url
    
    # Method 2: Try individual MySQL variables
    mysql_host = os.environ.get('MYSQLHOST')
    mysql_user = os.environ.get('MYSQLUSER')
    mysql_password = os.environ.get('MYSQLPASSWORD')
    mysql_database = os.environ.get('MYSQLDATABASE')
    mysql_port = os.environ.get('MYSQLPORT', '3306')
    
    if all([mysql_host, mysql_user, mysql_password, mysql_database]):
        # Build DATABASE_URL from individual variables
        database_url = f'mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}'
        return database_url
    
    # Fallback to local development database
    return 'mysql+pymysql://root:Madhup580%408019@127.0.0.1:3306/cursor_platform'

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Get DATABASE_URL - try environment variables first, then fallback to local
    SQLALCHEMY_DATABASE_URI = _get_database_url()
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,  # Verify connections before using
        'max_overflow': 20,
        'connect_args': {
            'connect_timeout': 10,
            'charset': 'utf8mb4'
        }
    }
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)  # Reduced to 1 hour for better security
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'  # Also used for CSRF
    
    # OpenAI API Configuration
    # Set OPENAI_API_KEY or AI_API_KEY in .env for AI assistant/interview features.
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_API_KEY') or ''
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Redis Configuration for Interview Memory Persistence
    REDIS_URL = os.environ.get('REDIS_URL') or os.environ.get('REDISCLOUD_URL') or None
    
    # OpenAI Pricing (per 1M tokens) - Updated pricing as of 2024
    # GPT-3.5-turbo pricing
    OPENAI_PRICING = {
        'gpt-3.5-turbo': {
            'input': 0.50 / 1_000_000,   # $0.50 per 1M input tokens
            'output': 1.50 / 1_000_000   # $1.50 per 1M output tokens
        },
        'gpt-4': {
            'input': 30.00 / 1_000_000,   # $30 per 1M input tokens
            'output': 60.00 / 1_000_000   # $60 per 1M output tokens
        },
        'gpt-4-turbo': {
            'input': 10.00 / 1_000_000,   # $10 per 1M input tokens
            'output': 30.00 / 1_000_000   # $30 per 1M output tokens
        }
    }
    
    # Cost-saving settings
    AI_CHAT_MAX_TOKENS_DEFAULT = 1500  # Default max tokens
    AI_CHAT_MAX_TOKENS_SIMPLE = 500   # For short/simple questions
    AI_CHAT_MAX_TOKENS_COMPLEX = 2000  # For complex questions
    
    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx', 'png', 'jpg', 'jpeg'}
    
    # Compiler API settings (using online compiler API)
    COMPILER_API_URL = 'https://api.jdoodle.com/v1/execute'
    COMPILER_CLIENT_ID = os.environ.get('COMPILER_CLIENT_ID') or ''
    COMPILER_CLIENT_SECRET = os.environ.get('COMPILER_CLIENT_SECRET') or ''
    
    # AI Chatbot settings (using OpenAI or similar)
    AI_API_KEY = os.environ.get('AI_API_KEY') or os.environ.get('OPENAI_API_KEY') or ''
    AI_API_URL = os.environ.get('AI_API_URL') or 'https://api.openai.com/v1/chat/completions'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
