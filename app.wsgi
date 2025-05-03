# app.wsgi
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app from api/app.py
from app import app as application

# For Render, the application object must be named 'application'
if __name__ == "__main__":
    application.run()
