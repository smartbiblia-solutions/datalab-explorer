# config.py
import os

# --- Core Settings ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'you-should-change-this')
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance/app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# --- Module Switches ---
# Set these to True or False to enable or disable modules
ENABLE_EMBEDDING_ATLAS = True
ENABLE_PLAYGROUND_LAB = True
ENABLE_PLAYGROUND_GENERIC = False
