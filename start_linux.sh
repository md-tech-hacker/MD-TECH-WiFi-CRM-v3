#!/usr/bin/env bash
# MD TECH Wi-Fi CRM — Linux/macOS Launcher
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "    MD TECH — Open Wi-Fi CRM Launcher    "
echo "=========================================="

# Check for python3
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 could not be found. Please install Python 3.10 or newer."
    exit 1
fi

# Set up virtual environment if missing
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment in .venv..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install requirements
echo "Checking and installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Start application
echo "Starting MD TECH Wi-Fi CRM on http://127.0.0.1:8765 ..."
python3 run.py
