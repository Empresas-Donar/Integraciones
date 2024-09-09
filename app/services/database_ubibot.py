# Map models and data and upload new information of Ubibot API to the database

from app.models import UbibotChannels, UbibotSummary, UbibotFields
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DataError
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from app import db
import json
import uuid
from app.services.utils import is_valid_integer, clean_data, convert_to_chilean_time
from datetime import datetime, timedelta
import logging
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DataError, SQLAlchemyError

logging.basicConfig(level=logging.INFO, filename='updates.log', 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def manage_data_ubi(processed_data, data_type):
    model_mapping = {
        'channels': UbibotChannels,
        'summary': UbibotSummary
    }
    base_data_type = data_type.split('_')[0]
    
    if base_data_type not in model_mapping:
        print(f"Unknown data type: {base_data_type}")
        return
    
    model = model_mapping[base_data_type]

    if base_data_type == 'channels':
        db.session.query(model).delete() 
        data_dict = processed_data.to_dict(orient='records')
        new_data = []

        for item in data_dict:
            instance = model(**item)
            db.session.add(instance)
            new_data.append(item)
        try:
            db.session.commit()
            print(f"{len(new_data)} nuevos registros insertados en {base_data_type}.")
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error de integridad al insertar datos en {base_data_type}: {e}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error al insertar en la base de datos para {base_data_type}: {e}")

    elif base_data_type == 'summary':
        data_dict = processed_data.to_dict(orient='records')
        cleaned_data_dict = clean_data(data_dict) 

        if not cleaned_data_dict:
            print("No hay nuevos registros para insertar.")
            return

        try:
            select_query = """
            SELECT id, created_at, channel_id, date, hour
            FROM ubi_channel_summary
            WHERE created_at >= CURRENT_DATE - INTERVAL '11 days';
            """
            existing_records = db.session.execute(text(select_query)).fetchall()
            existing_records_set = set((row['created_at'], row['channel_id']) for row in existing_records)
            print(f"Filtrados {len(existing_records)} registros existentes en los últimos 11 días.")
        except Exception as e:
            print(f"Error al filtrar registros de la base de datos: {e}")
            return  

        filtered_data = [
            item for item in cleaned_data_dict
            if (item['created_at'], item['channel_id']) not in existing_records_set
        ]

        if not filtered_data:
            print("No hay nuevos registros para insertar después del filtrado.")
            return

        insert_statement = """
        INSERT INTO ubi_channel_summary (id, created_at, channel_id, date, hour)
        VALUES (:id, :created_at, :channel_id, :date, :hour)
        ON CONFLICT (created_at, channel_id)
        DO NOTHING;
        """

        try:
            db.session.execute(
                text(insert_statement), 
                filtered_data  
            )
            db.session.commit()
            print(f"{len(filtered_data)} nuevos registros insertados con éxito en {base_data_type}.")
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error de integridad al insertar datos en {base_data_type}: {e}")
        except DataError as e:
            db.session.rollback()
            print(f"Error de datos al insertar en la base de datos para {base_data_type}: {e}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error al insertar en la base de datos para {base_data_type}: {e}")

def manage_fields_ubi(df, batch_size=200):

    try:
        select_query = """
        SELECT created_at, channel_id, name, avg, count, min, max, date, hour, summary_id
        FROM ubi_channels_fields
        WHERE created_at >= CURRENT_DATE - INTERVAL '11 days';
        """
        result = db.session.execute(text(select_query))
        existing_records = result.fetchall() 
        print(f"Filtrados {len(existing_records)} registros existentes de los últimos 11 días.")
    except Exception as e:
        print(f"Error al filtrar registros de la base de datos: {e}")
        return  

    df = df.dropna(subset=['channel_id', 'created_at'])  
    df['avg'] = df['avg'].fillna(0)  
    df['count'] = df['count'].fillna(0) 
    df['min'] = df['min'].fillna(0)  
    df['max'] = df['max'].fillna(0) 


    data_dicts = df.to_dict(orient='records')


    insert_statement = """
    INSERT INTO ubi_channels_fields (created_at, channel_id, name, avg, count, min, max, date, hour, summary_id)
    VALUES (:created_at, :channel_id, :name, :avg, :count, :min, :max, :date, :hour, :summary_id)
    ON CONFLICT (created_at, channel_id, name)
    DO UPDATE SET 
        avg = EXCLUDED.avg,
        count = EXCLUDED.count,
        min = EXCLUDED.min,
        max = EXCLUDED.max
    WHERE ubi_channels_fields.count < 12;
    """
    
    try:

        for i in range(0, len(data_dicts), batch_size):
            batch = data_dicts[i:i + batch_size]
            db.session.execute(
                text(insert_statement),
                batch  
            )
            db.session.commit()  
            print(f"Insertados/actualizados {len(batch)} registros en el lote {i // batch_size + 1}.")
        
        print(f"Se completaron {len(data_dicts)} registros insertados/actualizados en total.")
    
    except IntegrityError as e:
        db.session.rollback()  
        print(f"Error al insertar/actualizar registros: {e}")
    except Exception as e:
        db.session.rollback()
        print(f"Error inesperado: {e}")