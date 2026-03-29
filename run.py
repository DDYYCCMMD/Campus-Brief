"""
run.py — CampusBrief entry point
Run from project root: python run.py
"""

from src.server import app
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
