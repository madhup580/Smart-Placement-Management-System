#!/bin/bash

echo "========================================"
echo "Starting Interview Preparation Platform"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

echo "[1/3] Checking database connection..."
python3 test_connection.py
if [ $? -ne 0 ]; then
    echo ""
    echo "WARNING: Database connection test failed"
    echo "Please check your database configuration"
    echo ""
    read -p "Press enter to continue anyway..."
fi

echo ""
echo "[2/3] Starting Flask server..."
echo "Server will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py

