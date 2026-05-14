# ⚡ Quick Start Guide

## 🎯 Fastest Way to Run

### 1️⃣ Backend (Terminal 1)

```bash
# Windows
cd backend
python app.py

# Mac/Linux
cd backend
python3 app.py
```

**Backend will run on:** http://localhost:5000

### 2️⃣ Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

**Frontend will run on:** http://localhost:3000

### 3️⃣ Open Browser

Go to: **http://localhost:3000**

---

## 📦 First Time Setup

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt

# Check if database exists (skip if you know it exists)
python check_database.py

# Initialize tables (safe to run - won't delete existing data)
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"

# Start the app
python app.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## ✅ That's It!

The project should now be running. If you encounter errors, check the full `SETUP_GUIDE.md` for detailed troubleshooting.
