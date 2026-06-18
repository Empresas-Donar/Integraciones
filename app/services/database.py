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
        logging.info(f"Procesando {len(processed_data)} registros de sensores...")

        rows_to_upsert = []

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

                # Normalizar created_at a naive (sin timezone)
                if hasattr(created_at, 'tzinfo') and created_at.tzinfo is not None:
                    created_at_naive = created_at.replace(tzinfo=None)
                else:
                    created_at_naive = created_at

                rows_to_upsert.append({
                    "sensor_id": sensor_id,
                    "name": item.get("name"),
                    "unit": item.get("unit"),
                    "values": item.get("values"),
                    "created_at": created_at_naive,
                    "date": item.get("date"),
                    "hour": item.get("hour"),
                    "zone_id": zone_id,
                    "farm_id": farm_id,
                })

            except KeyError as e:
                logging.error(f"Error: Falta la clave {e} en el registro {item}")

        if rows_to_upsert:
            try:
                logging.info(f"Upserting {len(rows_to_upsert)} registros de sensores...")
                # ON CONFLICT en la clave natural (date, sensor_id, zone_id): actualiza el valor
                # si la API entrega un dato revisado para ese día
                upsert_sql = text("""
                    INSERT INTO wc_zones_sensors
                        (sensor_id, name, unit, values, created_at, date, hour, zone_id, farm_id)
                    VALUES
                        (:sensor_id, :name, :unit, :values, :created_at, :date, :hour, :zone_id, :farm_id)
                    ON CONFLICT (date, sensor_id, zone_id)
                    DO UPDATE SET
                        values     = EXCLUDED.values,
                        created_at = EXCLUDED.created_at,
                        unit       = EXCLUDED.unit
                """)
                db.session.execute(upsert_sql, rows_to_upsert)
                db.session.commit()
                logging.info(f"Upsert completado: {len(rows_to_upsert)} registros procesados")
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error en upsert de sensores: {e}")
        else:
            logging.info("No hay registros de sensores para procesar")

    elif data_type in ['zones', 'zones_imaipo']:
        farm_id = int(processed_data['farm_id'].iloc[0]) 
        db.session.query(model).filter_by(farm_id=farm_id).delete()  
        db.session.commit()
        data_dict = processed_data.to_dict(orient='records')
        new_data = []
    
        valid_cols = {c.key for c in model.__table__.columns}
        for item in data_dict:
            if item['id'] is None:
                continue

            filtered = {k: v for k, v in item.items() if k in valid_cols}
            instance = model(**filtered)
            db.session.add(instance)
            new_data.append(filtered)
    
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
