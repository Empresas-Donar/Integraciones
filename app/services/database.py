# Map models and data and upload new information to the database
from app.models import WC_Farms_Zones, WCFarmsIrrigation, WCFarmsRealIrrigation, WCZonesSensors
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from app import db
import json
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
        logging.warning(f"Tipo de dato desconocido: {data_type}")
        return

    if data_type == "combined":
        # Optimización: cargar registros existentes en memoria una sola vez
        logging.info(f"Procesando {len(processed_data)} registros de sensores...")

        try:
            # Obtener registros existentes de los últimos 11 días en una sola query
            existing_query = text("""
                SELECT created_at, sensor_id, farm_id, zone_id
                FROM wc_zones_sensors
                WHERE created_at >= CURRENT_DATE - INTERVAL '11 days'
            """)
            existing_results = db.session.execute(existing_query).fetchall()
            existing_set = set(
                (str(row[0]), str(row[1]), str(row[2]), str(row[3]) if row[3] else None)
                for row in existing_results
            )
            logging.info(f"Cargados {len(existing_set)} registros existentes en memoria")
        except Exception as e:
            logging.error(f"Error cargando registros existentes: {e}")
            existing_set = set()

        records_to_add = []

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

                # Verificar en memoria en lugar de query individual
                key = (str(created_at), str(sensor_id), farm_id, zone_id)
                if key not in existing_set:
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
                logging.error(f"Error: Falta la clave {e} en el registro {item}")

        if records_to_add:
            try:
                logging.info(f"Insertando {len(records_to_add)} nuevos registros...")
                db.session.bulk_save_objects(records_to_add)
                db.session.commit()
                logging.info(f"Insertados {len(records_to_add)} registros de sensores exitosamente")
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error inserting records: {e}")
        else:
            logging.info("No hay nuevos registros de sensores para insertar")

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
