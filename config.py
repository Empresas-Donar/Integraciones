# Get the necessary sensitive variables

import os
from app.environment import ENV, DATABASE_URL

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False') == 'True'
    DEBUG = os.getenv('DEBUG', 'False') == 'True'