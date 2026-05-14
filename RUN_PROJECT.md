# 🚀 How to Run the Project

## 📋 Prerequisites Check

```bash
# Check Python version (need 3.11+)
python --version

# Check Node.js version (need 18+)
node --version

# Check npm version
npm --version

# Check MySQL (should be running)
mysql --version
```

---

## 🔧 Complete Setup (First Time Only)

### Step 1: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install all dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Check if database exists (optional)
python check_database.py

# If database doesn't exist, create it:
# mysql -u root -p
# CREATE DATABASE cursor_platform;
# EXIT;

# Initialize/Update database tables (safe to run - won't delete existing data)
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database tables initialized!')"
```

### Step 2: Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install
```

### Step 3: (Optional) Redis Setup

```bash
# Windows: Download and install Redis
# Mac:
brew install redis
brew services start redis

# Linux:
sudo apt-get install redis-server
sudo systemctl start redis

# Or use Docker:
docker run -d -p 6379:6379 redis
```

---

## ▶️ Running the Project

### Method 1: Manual (Recommended for Development)

#### Terminal 1 - Backend
```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
python app.py
```

**Expected Output:**
```
[INFO] Flask app starting on http://0.0.0.0:5000
[OK] Database connected
[OK] WebSocket support initialized
```

#### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

**Expected Output:**
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

### Method 2: Using Batch Files (Windows)

#### Backend
```bash
cd backend
start_server.bat
```

#### Frontend
```bash
cd frontend
npm run dev
```

### Method 3: Using Shell Scripts (Mac/Linux)

#### Backend
```bash
cd backend
chmod +x start_server.sh
./start_server.sh
```

#### Frontend
```bash
cd frontend
npm run dev
```

---

## 🌐 Access the Application

1. **Frontend**: http://localhost:3000
2. **Backend API**: http://localhost:5000
3. **API Info**: http://localhost:5000/api

---

## 🧪 Testing

### Run Unit Tests
```bash
cd backend
pytest
```

### Run Tests with Coverage
```bash
cd backend
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Load Tests
```bash
# Start backend first
cd backend
python app.py

# In another terminal
cd backend
locust -f tests/load/locustfile.py --host=http://localhost:5000
# Open http://localhost:8089 in browser
```

---

## 🔍 Verify Everything Works

### 1. Check Backend
```bash
curl http://localhost:5000
# Should return: {"status": "ok", ...}
```

### 2. Check Frontend
Open http://localhost:3000 in browser
Should see login page

### 3. Check Database
```bash
mysql -u root -p cursor_platform -e "SHOW TABLES;"
# Should show tables: users, questions, etc.
```

### 4. Check Redis (if installed)
```bash
redis-cli ping
# Should return: PONG
```

---

## 🛠️ Common Commands

### Backend Commands

```bash
# Run Flask app
python app.py

# Run with auto-reload
flask run --reload

# Run with Gunicorn (production)
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Run tests
pytest
pytest -v
pytest tests/test_auth.py

# Check database
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); print('DB OK' if db.engine.connect() else 'DB FAIL')"
```

### Frontend Commands

```bash
# Development server
npm run dev

# Production build
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

### Database Commands

```bash
# Connect to MySQL
mysql -u root -p

# Use database
USE cursor_platform;

# Show all tables
SHOW TABLES;

# Check users table
SELECT * FROM users LIMIT 5;
```

---

## 🐛 Troubleshooting

### Backend Won't Start

**Error: Port 5000 already in use**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:5000 | xargs kill -9
```

**Error: Module not found**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Error: Database connection failed**
```bash
# Check MySQL is running
# Windows: Services → MySQL
# Mac: brew services list
# Linux: sudo systemctl status mysql

# Test connection
mysql -u root -p -e "SELECT 1"
```

### Frontend Won't Start

**Error: Port 3000 already in use**
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:3000 | xargs kill -9
```

**Error: npm install fails**
```bash
# Clear cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Database Issues

**Error: Table doesn't exist**
```bash
cd backend
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

**Error: Access denied**
```bash
# Check MySQL user permissions
mysql -u root -p
GRANT ALL PRIVILEGES ON cursor_platform.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

---

## 📊 Service Status Check

### Check if services are running:

```bash
# Backend (should return JSON)
curl http://localhost:5000

# Frontend (should return HTML)
curl http://localhost:3000

# MySQL
mysql -u root -p -e "SELECT 1"

# Redis (if installed)
redis-cli ping
```

---

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Start Backend | `cd backend && python app.py` |
| Start Frontend | `cd frontend && npm run dev` |
| Run Tests | `cd backend && pytest` |
| Build Frontend | `cd frontend && npm run build` |
| Check Backend | `curl http://localhost:5000` |
| Check Frontend | Open http://localhost:3000 |

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
# Serve dist/ folder with nginx or similar
```

---

## 📝 Environment Variables

Create `backend/.env`:
```env
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/cursor_platform
JWT_SECRET_KEY=your-secret-key
SECRET_KEY=your-secret-key
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your-openai-key
FLASK_ENV=development
```

---

## ✅ Success Indicators

✅ Backend running: `{"status": "ok"}` at http://localhost:5000  
✅ Frontend running: Login page at http://localhost:3000  
✅ Database connected: No errors in backend logs  
✅ Redis connected: `[Security] ✅ Redis connected` in logs  

---

## 🆘 Still Having Issues?

1. Check `backend/logs/` for error logs
2. Check browser console (F12) for frontend errors
3. Verify all prerequisites are installed
4. Check firewall/antivirus isn't blocking ports
5. Review `SETUP_GUIDE.md` for detailed troubleshooting
