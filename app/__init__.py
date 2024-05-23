from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from config import Config


db = SQLAlchemy()  # Creación de la instancia de SQLAlchemy

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)  # Inicialización de SQLAlchemy con la app de Flask
    migrate = Migrate(app, db)  # Inicializa Flask-Migrate

    with app.app_context():
        check_and_initialize_tables()  # Chequear e inicializar las tablas dentro del contexto de la aplicación

    # Otras configuraciones o inicializaciones
    return app

def check_and_initialize_tables():
    inspector = inspect(db.engine)
    existing_tables_before = inspector.get_table_names()  # Tablas antes de cualquier operación
    db.create_all()  # Intenta crear todas las tablas definidas en los modelos
    existing_tables_after = inspector.get_table_names()  # Tablas después de la operación

    new_tables = set(existing_tables_after) - set(existing_tables_before)
    if new_tables:
        print(f"Se crearon las siguientes nuevas tablas: {', '.join(new_tables)}")
    else:
        print("No había ninguna tabla nueva por crear.")

