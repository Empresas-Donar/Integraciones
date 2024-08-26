# Map models and data and upload new information to the database
from app.models import WC_Farms_Zones, WCFarmsIrrigation, WCFarmsRealIrrigation, WCZonesSensors
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from app import db
import json

def manage_data(processed_data, data_type):
    model_mapping = {
        'zones': WC_Farms_Zones,
        'irrigations': WCFarmsIrrigation,
        'realirrigations': WCFarmsRealIrrigation,
    }
    
    model = model_mapping.get(data_type)
    
    if not model and data_type != "combined_measures_sensor_data":
        print(f"Tipo de dato desconocido: {data_type}")
        return
    
    if data_type == "combined_measures_sensor_data":
        records_to_add = []
        for item in processed_data:
            try:
                created_at = item['created_at']
                sensor_id = item['sensor_id']
                existing_record = WCZonesSensors.query.filter_by(
                    created_at=created_at,
                    sensor_id=sensor_id
                ).first()
                
                if not existing_record:
                    new_record = WCZonesSensors(
                        sensor_id = sensor_id,
                        name=item["name"],
                        unit=item["unit"],
                        values=item["values"],
                        created_at=created_at,
                        date=item["date"],
                        hour=item["hour"]
                    )
                    records_to_add.append(new_record)
            except KeyError as e:
                print(f"Error: Falta la clave {e} en el registro {item}")
        
        if records_to_add:
            try:
                db.session.bulk_save_objects(records_to_add)
                db.session.commit()
                print(f"{len(records_to_add)} nuevos registros insertados en la tabla WCZonesSensors.")
            except Exception as e:
                db.session.rollback()
                print(f"Error inserting records: {e}")

    elif data_type == 'zones':
        db.session.query(model).delete()
        data_dict = processed_data.to_dict(orient='records')
        new_data = []
        for item in data_dict:
            instance = model(**item)
            db.session.add(instance)
            new_data.append(item)
        try:
            db.session.commit()
            print(f"{len(new_data)} nuevos registros insertados en {data_type}.")
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error de integridad al insertar datos en {data_type}: {e}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error al insertar en la base de datos para {data_type}: {e}")
    else:
        existing_ids = set(id[0] for id in db.session.query(model.id).all())
        data_dict = processed_data.to_dict(orient='records')
        new_data = []
        for item in data_dict:
            if 'id' in item and item['id'] not in existing_ids:
                instance = model(**item)
                db.session.add(instance)
                new_data.append(item)
        try:
            db.session.commit()
            print(f"{len(new_data)} nuevos registros insertados en {data_type}.")
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error de integridad al insertar datos en {data_type}: {e}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error al insertar en la base de datos para {data_type}: {e}")