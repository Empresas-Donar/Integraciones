# Create the SQLAlchemy instance and check the tables before any operation.

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from config import Config

db = SQLAlchemy()  

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)  
    migrate = Migrate(app, db)  
    with app.app_context():
        check_and_initialize_tables()  
    return app

# Check the tables

def check_and_initialize_tables():
    inspector = inspect(db.engine)
    existing_tables_before = inspector.get_table_names()  
    db.create_all()  
    existing_tables_after = inspector.get_table_names()  
    new_tables = set(existing_tables_after) - set(existing_tables_before)
    if new_tables:
        print(f"Se crearon las siguientes nuevas tablas: {', '.join(new_tables)}")
    else:
        print("No había ninguna tabla nueva por crear.")