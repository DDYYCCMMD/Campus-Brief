"""
run.py — CampusBrief entry point
Run from project root: python run.py
"""

import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.server import app

if __name__ == "__main__":
    app.run(debug=False, port=5000)
