# Database Setup Guide

## 🔍 Check if Database Already Exists

### Quick Check
```bash
cd backend
python check_database.py
```

This will tell you:
- ✅ If database exists
- ✅ If you can connect to it
- ✅ What tables exist
- ❌ If database needs to be created

### Manual Check (MySQL CLI)
```bash
mysql -u root -p -e "SHOW DATABASES LIKE 'cursor_platform';"
```

---

## 📊 Database Setup Options

### Option 1: Database Already Exists ✅

**If your database already exists, you only need to:**

```bash
cd backend
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all(); print('Tables initialized!')"
```

This will:
- ✅ Connect to existing database
- ✅ Create missing tables (if any)
- ✅ **NOT** recreate the database
- ✅ **NOT** delete existing data

### Option 2: Database Doesn't Exist ❌

**If database doesn't exist, create it first:**

```bash
# Connect to MySQL
mysql -u root -p

# Create database
CREATE DATABASE cursor_platform;
EXIT;

# Then initialize tables
cd backend
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all(); print('Database and tables initialized!')"
```

---

## 🔄 What `db.create_all()` Does

**Important:** `db.create_all()` only creates **tables**, not the database itself.

- ✅ Creates tables if they don't exist
- ✅ **Does NOT** delete existing tables
- ✅ **Does NOT** delete existing data
- ✅ **Does NOT** recreate the database
- ✅ Safe to run multiple times

**Example:**
```python
# First run: Creates all tables
db.create_all()  # ✅ Creates: users, questions, quizzes, etc.

# Second run: Does nothing (tables already exist)
db.create_all()  # ✅ No changes, tables already exist

# Safe to run anytime!
```

---

## 🛠️ Common Scenarios

### Scenario 1: Fresh Installation
```bash
# 1. Create database
mysql -u root -p
CREATE DATABASE cursor_platform;
EXIT;

# 2. Initialize tables
cd backend
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Scenario 2: Database Exists, Tables Missing
```bash
# Just initialize tables
cd backend
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Scenario 3: Everything Already Exists
```bash
# No action needed! Just run the app:
cd backend
python app.py
```

### Scenario 4: Want to Start Fresh (⚠️ Deletes All Data)
```bash
# ⚠️ WARNING: This deletes all data!
mysql -u root -p
DROP DATABASE cursor_platform;
CREATE DATABASE cursor_platform;
EXIT;

# Then initialize
cd backend
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

---

## ✅ Verification

### Check Database Connection
```bash
cd backend
python check_database.py
```

### Check Tables
```bash
mysql -u root -p cursor_platform -e "SHOW TABLES;"
```

### Check Table Structure
```bash
mysql -u root -p cursor_platform -e "DESCRIBE users;"
```

---

## 📝 Summary

| Situation | Action Needed |
|-----------|---------------|
| Database exists, tables exist | ✅ Nothing - just run `python app.py` |
| Database exists, tables missing | ✅ Run `db.create_all()` |
| Database doesn't exist | ✅ Create database, then run `db.create_all()` |
| Want to reset everything | ⚠️ Drop database, create new, run `db.create_all()` |

---

## 🎯 Quick Reference

```bash
# Check if database exists
python check_database.py

# Initialize/update tables (safe to run multiple times)
python -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"

# Start the app
python app.py
```
