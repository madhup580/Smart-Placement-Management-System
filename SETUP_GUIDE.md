# 🚀 Complete Setup & Run Guide

## 📋 Prerequisites

### Required Software
- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Node.js 18+** and npm ([Download](https://nodejs.org/))
- **MySQL 8.0+** ([Download](https://dev.mysql.com/downloads/))
- **Redis** (Optional but recommended) ([Download](https://redis.io/download))
- **Git** ([Download](https://git-scm.com/downloads))

### Optional (for Docker sandbox)
- **Docker Desktop** ([Download](https://www.docker.com/products/docker-desktop))

---

## 🔧 Backend Setup

### Step 1: Navigate to Backend Directory
```bash
cd backend
```

### Step 2: Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Database

#### Option A: Using Environment Variables
Create `.env` file in `backend/` directory:
```env
DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/cursor_platform
JWT_SECRET_KEY=your-secret-key-here
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your-openai-api-key
```

#### Option B: Update `config.py`
Edit `backend/config.py` and update database connection string:
```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:your_password@localhost:3306/cursor_platform'
```

### Step 5: Check/Create Database
```bash
# Check if database already exists
mysql -u root -p -e "SHOW DATABASES LIKE 'cursor_platform';"

# If database doesn't exist, create it:
mysql -u root -p
CREATE DATABASE cursor_platform;
EXIT;

# If database already exists, skip the creation step above
```

### Step 6: Initialize/Update Database Tables
```bash
# From backend directory
# This creates tables if they don't exist, but won't recreate the database
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database tables initialized!')"
```

Or using Flask CLI:
```bash
flask db init  # If using Flask-Migrate
flask db migrate -m "Initial migration"
flask db upgrade
```

### Step 7: (Optional) Start Redis
```bash
# Windows (if installed)
redis-server

# Mac (Homebrew)
brew services start redis

# Linux
sudo systemctl start redis

# Or using Docker
docker run -d -p 6379:6379 redis
```

---

## 🎨 Frontend Setup

### Step 1: Navigate to Frontend Directory
```bash
cd frontend
```

### Step 2: Install Node Dependencies
```bash
npm install
```

### Step 3: (Optional) Configure Environment
Create `.env` file in `frontend/` directory:
```env
VITE_API_BASE_URL=http://localhost:5000/api/v1
```

---

## ▶️ Running the Project

### Option 1: Quick Start (Windows)

#### Backend (Terminal 1)
```bash
cd backend
python app.py
```
Or use the batch file:
```bash
cd backend
start_server.bat
```

#### Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

### Option 2: Quick Start (Mac/Linux)

#### Backend (Terminal 1)
```bash
cd backend
python3 app.py
```
Or use the shell script:
```bash
cd backend
chmod +x start_server.sh
./start_server.sh
```

#### Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

### Option 3: Production Mode

#### Backend
```bash
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Frontend
```bash
cd frontend
npm run build
# Serve the dist/ folder with a web server
```

---

## 🔍 Verify Installation

### Check Backend
Open browser: http://localhost:5000
Should see: `{"status": "ok", "message": "Interview Preparation Platform API"}`

### Check Frontend
Open browser: http://localhost:3000
Should see: Login page

### Check Database Connection
```bash
cd backend
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); print('Database connected!' if db.engine.connect() else 'Connection failed')"
```

### Check Redis (if installed)
```bash
redis-cli ping
# Should return: PONG
```

---

## 📝 Complete Command List

### Backend Commands

```bash
# Navigate to backend
cd backend

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Flask app
python app.py

# Run with auto-reload (development)
flask run --reload

# Run with Gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Run tests
pytest
pytest --cov=. --cov-report=html

# Run load tests
locust -f tests/load/locustfile.py --host=http://localhost:5000

# Check database connection
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.engine.connect()"
```

### Frontend Commands

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint

# Check for updates
npm outdated
```

### Database Commands

```bash
# Connect to MySQL
mysql -u root -p

# Create database
CREATE DATABASE cursor_platform;

# Show databases
SHOW DATABASES;

# Use database
USE cursor_platform;

# Show tables
SHOW TABLES;
```

### Redis Commands

```bash
# Start Redis (Windows)
redis-server

# Start Redis (Mac/Linux)
redis-server
# Or
sudo systemctl start redis

# Check Redis status
redis-cli ping

# Connect to Redis CLI
redis-cli

# View all keys
redis-cli KEYS *

# Clear all keys
redis-cli FLUSHALL
```

---

## 🐛 Troubleshooting

### Backend Issues

#### Port 5000 already in use
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:5000 | xargs kill -9
```

#### Database connection error
```bash
# Check MySQL is running
# Windows: Services → MySQL
# Mac: brew services list
# Linux: sudo systemctl status mysql

# Test connection
mysql -u root -p -e "SELECT 1"
```

#### Module not found errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend Issues

#### Port 3000 already in use
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:3000 | xargs kill -9
```

#### npm install fails
```bash
# Clear cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### React build errors
```bash
# Update dependencies
npm update

# Check Node version (should be 18+)
node --version
```

### Redis Issues

#### Redis not starting
```bash
# Check if Redis is installed
redis-cli --version

# Install Redis (Mac)
brew install redis

# Install Redis (Linux)
sudo apt-get install redis-server

# Or use Docker
docker run -d -p 6379:6379 redis
```

---

## 📊 Service URLs

| Service | URL | Description |
|--------|-----|-------------|
| Backend API | http://localhost:5000 | Flask API server |
| Frontend Dev | http://localhost:3000 | React dev server |
| Frontend Prod | http://localhost:5000 | Served by Flask (after build) |
| MySQL | localhost:3306 | Database server |
| Redis | localhost:6379 | Cache/Queue server |

---

## 🎯 Quick Start Checklist

- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] MySQL 8.0+ installed and running
- [ ] Redis installed (optional)
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Database created (`cursor_platform`)
- [ ] Database tables initialized
- [ ] `.env` file configured (optional)
- [ ] Backend running on port 5000
- [ ] Frontend running on port 3000

---

## 🚀 Production Deployment

### Backend (Production)
```bash
cd backend
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
```

### Frontend (Production)
```bash
cd frontend
npm run build
# Copy dist/ contents to your web server
```

### Environment Variables (Production)
```bash
export FLASK_ENV=production
export DATABASE_URL=mysql+pymysql://user:pass@host:3306/db
export REDIS_URL=redis://host:6379
export JWT_SECRET_KEY=strong-secret-key
export SECRET_KEY=strong-secret-key
```

---

## 📚 Additional Resources

- **Backend API Docs**: http://localhost:5000/api
- **Test Coverage**: `backend/htmlcov/index.html` (after running pytest with coverage)
- **Load Test UI**: http://localhost:8089 (when running Locust)

---

## 💡 Tips

1. **Use Virtual Environment**: Always use a virtual environment for Python
2. **Use .env Files**: Store sensitive data in `.env` files (not in git)
3. **Check Logs**: Backend logs are in `backend/logs/`
4. **Hot Reload**: Frontend auto-reloads on changes (Vite)
5. **Database Migrations**: Use Flask-Migrate for schema changes
6. **Redis Optional**: System works without Redis (uses in-memory fallback)

---

## 🆘 Need Help?

1. Check logs: `backend/logs/audit.log` and `backend/logs/security.log`
2. Check browser console for frontend errors
3. Check terminal output for backend errors
4. Verify all services are running (MySQL, Redis)
5. Check firewall/antivirus isn't blocking ports
