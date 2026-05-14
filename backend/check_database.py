"""
Check if database exists and is accessible
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def check_database():
    """Check if database exists and is accessible"""
    try:
        # Get database connection details
        db_url = os.environ.get('DATABASE_URL', '')
        
        # Parse connection string or use defaults
        if db_url:
            # Parse mysql+pymysql://user:pass@host:port/dbname
            if 'mysql+pymysql://' in db_url:
                parts = db_url.replace('mysql+pymysql://', '').split('@')
                if len(parts) == 2:
                    user_pass = parts[0].split(':')
                    host_db = parts[1].split('/')
                    if len(host_db) == 2:
                        host_port = host_db[0].split(':')
                        user = user_pass[0]
                        password = user_pass[1] if len(user_pass) > 1 else ''
                        host = host_port[0]
                        port = int(host_port[1]) if len(host_port) > 1 else 3306
                        database = host_db[1]
                    else:
                        raise ValueError("Invalid database URL format")
                else:
                    raise ValueError("Invalid database URL format")
            else:
                raise ValueError("Only mysql+pymysql:// URLs are supported")
        else:
            # Use defaults from config
            user = os.environ.get('DB_USER', 'root')
            password = os.environ.get('DB_PASSWORD', '')
            host = os.environ.get('DB_HOST', 'localhost')
            port = int(os.environ.get('DB_PORT', 3306))
            database = os.environ.get('DB_NAME', 'cursor_platform')
        
        # First, connect without database to check if it exists
        print(f"Connecting to MySQL server at {host}:{port}...")
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            charset='utf8mb4'
        )
        
        try:
            with connection.cursor() as cursor:
                # Check if database exists
                cursor.execute("SHOW DATABASES LIKE %s", (database,))
                result = cursor.fetchone()
                
                if result:
                    print(f"✅ Database '{database}' exists!")
                    
                    # Try to use the database
                    cursor.execute(f"USE {database}")
                    print(f"✅ Successfully connected to database '{database}'")
                    
                    # Check if tables exist
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    
                    if tables:
                        print(f"✅ Database has {len(tables)} table(s):")
                        for table in tables:
                            print(f"   - {table[0]}")
                    else:
                        print("⚠️  Database exists but has no tables")
                        print("   Run: python -c \"from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()\"")
                    
                    return True
                else:
                    print(f"❌ Database '{database}' does NOT exist")
                    print(f"\nTo create it, run:")
                    print(f"  mysql -u {user} -p")
                    print(f"  CREATE DATABASE {database};")
                    print(f"  EXIT;")
                    return False
        finally:
            connection.close()
            
    except pymysql.Error as e:
        print(f"❌ MySQL Error: {e}")
        print("\nPlease check:")
        print("1. MySQL server is running")
        print("2. Username and password are correct")
        print("3. Database connection settings in .env or config.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    check_database()
