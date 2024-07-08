# Map models and data and upload new information of Ubibot API to the database

from app.models import UbibotChannels, UbibotSummary, UbibotFields
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DataError
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from app import db
import json
import uuid
from app.services.utils import is_valid_integer, clean_data
from datetime import datetime

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
        existing_ids = {id[0]: id for id in db.session.query(model.id).all()}
        data_dict = processed_data.to_dict(orient='records')
        new_data = []
        updated_data = 0
        
        for item in data_dict:
            if 'id' in item:
                if item['id'] in existing_ids:
                    db.session.query(model).filter(model.id == item['id']).update(item)
                    updated_data += 1
                else:
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
        new_data = []
        for item in cleaned_data_dict:
            if not is_valid_integer(item['channel_id']):
                print(f"Invalid channel_id: {item['channel_id']}")
                continue
            if 'id' not in item or not item['id']:
                item['id'] = uuid.uuid4().hex
            channel_id = item['channel_id']
            created_at = item['created_at']
            with db.session.no_autoflush:
                exists = db.session.query(model).filter_by(channel_id=channel_id, created_at=created_at).first()
            if not exists:
                instance = model(**item)
                db.session.add(instance)
                new_data.append(item)
        try:
            db.session.commit()
            print(f"{len(new_data)} nuevos registros insertados en {base_data_type}.")
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error de integridad al insertar datos en {base_data_type}: {e}")
        except DataError as e:
            db.session.rollback()
            print(f"Error de datos al insertar en la base de datos para {base_data_type}: {e}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error al insertar en la base de datos para {base_data_type}: {e}")

def manage_fields_ubi(df):
    df = df.dropna(subset=['channel_id', 'created_at'])
    df = df[df['channel_id'] < 100000]
    df = df[df['count'].fillna(0).apply(lambda x: x <= 24)]
    df['avg'] = df['avg'].fillna(0)
    df['count'] = df['count'].fillna(0)
    df['min'] = df['min'].fillna(0)
    df['max'] = df['max'].fillna(0)
    data_dicts = df.to_dict(orient='records')
    records_to_add = []
    for row in data_dicts:
        existing_record = UbibotFields.query.filter_by(
            channel_id=row['channel_id'],
            created_at=row['created_at'],
            name=row['name']
        ).first()
        if not existing_record:
            new_record = UbibotFields(
                summary_id=row['summary_id'],
                channel_id=row['channel_id'],
                created_at=row['created_at'],
                date=row['date'],
                hour=row['hour'],
                name=row['name'],
                avg=row['avg'],
                count=row['count'],
                min=row['min'],
                max=row['max']
            )
            records_to_add.append(new_record)
    if records_to_add:
        try:
            db.session.bulk_save_objects(records_to_add)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error inserting records: {e}")