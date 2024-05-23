from app.models import WC_Farms_Zones, WCFarmsIrrigation
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from app import db
import json

def manage_data(processed_data, data_type):
    model_mapping = {
        'zones': WC_Farms_Zones,
        'irrigations': WCFarmsIrrigation
    }

    model = model_mapping[data_type]
    existing_ids = set(id[0] for id in db.session.query(model.id).all())  # Asegúrate de que esto extrae correctamente los IDs.

    data_dict = processed_data.to_dict(orient='records')
    new_data = []

    for item in data_dict:
        if 'id' in item and item['id'] not in existing_ids:
            instance = model(**item)
            db.session.add(instance)  # Preparar para agregar el nuevo registro

    try:
        db.session.commit()  # Intentar hacer commit de los cambios en la base de datos
        print(f"{len(new_data)} nuevos registros insertados en {data_type}.")
    except IntegrityError as e:
        db.session.rollback()  # Revertir la transacción si hay un error de integridad
        print(f"Error de integridad al insertar datos en {data_type}: {e}")
    except SQLAlchemyError as e:
        db.session.rollback()  # Revertir la transacción si hay cualquier otro error de SQLAlchemy
        print(f"Error al insertar en la base de datos para {data_type}: {e}")










