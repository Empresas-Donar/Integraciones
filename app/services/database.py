# Map models and data and upload new information to the database
from app.models import WC_Farms_Zones, WCFarmsIrrigation, WCFarmsRealIrrigation, WCZonesSensors
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from app import db
import json

def manage_data(processed_data, data_type):
    print(f"Procesando data_type: {data_type}")
    print(f"Datos procesados recibidos, tamaño: {len(processed_data)}")

    model_mapping = {
        'zones': WC_Farms_Zones,
        'irrigations': WCFarmsIrrigation,
        'realirrigations': WCFarmsRealIrrigation,
        'zones_imaipo': WC_Farms_Zones,
        'irrigations_imaipo': WCFarmsIrrigation,
        'realirrigations_imaipo': WCFarmsRealIrrigation,
    }
    
    data_type = data_type.split('_')[0]
    print(f"Data type después del split: {data_type}")
    
    model = model_mapping.get(data_type)
    
    if not model and data_type != "combined":
        print(f"Tipo de dato desconocido: {data_type}")
        return
    
    if data_type == "combined":
        print("Procesando combined_measures_sensor_data")
        records_to_add = []
        print(f"Recibidos {len(processed_data)} registros")
        print("Últimas 10 fechas recibidas:")
        for item in processed_data[-10:]:  
            print(f"Sensor ID: {item.get('sensor_id')}, Fecha: {item.get('created_at')}")

        for item in processed_data:
            try:
                created_at = item.get('created_at')
                sensor_id = item.get('sensor_id')
                farmid = str(item.get('farmid')) 
                zoneid = item.get('zoneid')

                if pd.isna(zoneid):
                    zoneid = None
                else:
                    zoneid = str(zoneid)  

                if len(farmid) > 50:
                    print(f"WARNING: El farmid {farmid} excede los 50 caracteres para sensor ID: {sensor_id}")    

                print(f"Procesando sensor: {sensor_id}, farm_id: {farmid}, zoneid: {zoneid}, created_at: {created_at}")

                existing_record = WCZonesSensors.query.filter_by(
                    created_at=created_at,
                    sensor_id=sensor_id,
                    farmid=farmid,
                    zoneid=zoneid
                ).first()

                if not existing_record:
                    print(f"Agregando nuevo record para sensor: {sensor_id}")
                    new_record = WCZonesSensors(
                        sensor_id=sensor_id,
                        name=item.get("name"),
                        unit=item.get("unit"),
                        values=item.get("values"),
                        created_at=created_at,
                        date=item.get("date"),
                        hour=item.get("hour"),
                        zoneid=zoneid,
                        farmid=farmid  
                    )
                    records_to_add.append(new_record)

            except KeyError as e:
                print(f"Error: Falta la clave {e} en el registro {item}")

        print(f"Registros para insertar: {len(records_to_add)}")
        if records_to_add:
            try:
                print(f"Insertando {len(records_to_add)} registros en la base de datos...")
                db.session.bulk_save_objects(records_to_add)
                db.session.commit()
                print(f"{len(records_to_add)} nuevos registros insertados en las tablas correspondientes.")
            except Exception as e:
                db.session.rollback()
                print(f"Error inserting records: {e}")

    elif data_type in ['zones', 'zones_imaipo']:
        farmid = int(processed_data['farmid'].iloc[0]) 
        db.session.query(model).filter_by(farmid=farmid).delete()
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
            print(f"Error de integridad al insertar datos en {data_type}: {e.orig}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error al insertar en la base de datos para {data_type}: {e}")
