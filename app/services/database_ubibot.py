# Map models and data and upload new information of Ubibot API to the database

from app.models import UbibotChannels, UbibotSummary
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DataError
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from app import db
import json
import uuid

def is_valid_integer(value):
    try:
        if value is None or pd.isna(value):
            return False
        int_value = int(value)
        return True
    except (ValueError, OverflowError):
        return False

def clean_data(data_dict):
    cleaned_data = []
    for item in data_dict:
        cleaned_item = {}
        for key, value in item.items():
            if pd.isna(value):
                cleaned_item[key] = None
            else:
                cleaned_item[key] = value
        cleaned_data.append(cleaned_item)
    return cleaned_data

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
            for field in ['field1_count', 'field2_count', 'field3_count', 'field6_count', 'field9_count', 'field10_count']:
                if not is_valid_integer(item.get(field)):
                    item[field] = None
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