import os
from dotenv import load_dotenv

load_dotenv()  # Esto carga las variables de entorno desde el archivo .env

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key_if_none_found')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.getenv('DEBUG', 'False') == 'True'



