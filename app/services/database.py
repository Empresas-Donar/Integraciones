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
        'zones_imaipo': WC_Farms_Zones,
        'irrigations_imaipo': WCFarmsIrrigation,
        'realirrigations_imaipo': WCFarmsRealIrrigation,
    }
    
    data_type = data_type.split('_')[0]  
    model = model_mapping.get(data_type)
    
    if not model and data_type != "combined":
        print(f"Tipo de dato desconocido: {data_type}")
        return
    
    if data_type == "combined":

        records_to_add = []

        for item in processed_data[-10:]:  
            print(f"Sensor ID: {item.get('sensor_id')}, Fecha: {item.get('created_at')}")

        for item in processed_data:
            try:
                created_at = item.get('created_at')
                sensor_id = item.get('sensor_id')
                farm_id = str(item.get('farm_id'))  
                zone_id = item.get('zone_id')

                if pd.isna(zone_id):
                    zone_id = None
                else:
                    zone_id = str(zone_id)  

                if len(farm_id) > 50:
                    print(f"WARNING: El farm_id {farm_id} excede los 50 caracteres para sensor ID: {sensor_id}")    

                existing_record = WCZonesSensors.query.filter_by(
                    created_at=created_at,
                    sensor_id=sensor_id,
                    farm_id=farm_id,
                    zone_id=zone_id
                ).first()

                if not existing_record:
                    new_record = WCZonesSensors(
                        sensor_id=sensor_id,
                        name=item.get("name"),
                        unit=item.get("unit"),
                        values=item.get("values"),
                        created_at=created_at,
                        date=item.get("date"),
                        hour=item.get("hour"),
                        zone_id=zone_id,
                        farm_id=farm_id  
                    )
                    records_to_add.append(new_record)

            except KeyError as e:
                print(f"Error: Falta la clave {e} en el registro {item}")

        if records_to_add:
            try:

                db.session.bulk_save_objects(records_to_add)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error inserting records: {e}")

    elif data_type in ['zones', 'zones_imaipo']:
        farm_id = int(processed_data['farm_id'].iloc[0]) 
        db.session.query(model).filter_by(farm_id=farm_id).delete()  
        db.session.commit()
        data_dict = processed_data.to_dict(orient='records')
        new_data = []
    
        for item in data_dict:
            if item['id'] is None:
                continue  
        
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
        existing_records = {id_: status for id_, status in db.session.query(model.id, model.status).all()}
        data_dict = processed_data.to_dict(orient='records')
        new_data = []

        for item in data_dict:
            record_id = item.get('id')

            if record_id in existing_records:
                if existing_records[record_id] == "Running":
                    db.session.query(model).filter_by(id=record_id).delete()
                    instance = model(**item)
                    db.session.add(instance)

            else:
                instance = model(**item)
                db.session.add(instance)
                new_data.append(item)

        try:
            db.session.commit()
            print(f"{len(new_data)} nuevos registros insertados en {data_type}.")
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error de integridad al insertar datos en {data_type}: {e.orig}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error al insertar en la base de datos para {data_type}: {e}")
