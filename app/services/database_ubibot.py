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
import sys
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DataError, SQLAlchemyError

# Configurar logger para Google Cloud (stdout con formato estructurado)
logger = logging.getLogger('ubibot_database')
logger.setLevel(logging.INFO)

# Handler para stdout (Google Cloud captura esto)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log_ubibot_event(event_type, message, data=None, level="INFO"):
    """
    Log estructurado para Google Cloud Logging.
    Formato JSON amigable para filtrar en Cloud Logging.
    """
    log_entry = {
        "service": "ubibot_sync",
        "event_type": event_type,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }

    if data:
        log_entry["data"] = data

    log_message = json.dumps(log_entry, ensure_ascii=False, default=str)

    if level == "ERROR":
        logger.error(log_message)
    elif level == "WARNING":
        logger.warning(log_message)
    else:
        logger.info(log_message)

def manage_data_ubi(processed_data, data_type):
    model_mapping = {
        'channels': UbibotChannels,
        'summary': UbibotSummary
    }
    base_data_type = data_type.split('_')[0]

    log_ubibot_event(
        "SYNC_START",
        f"Iniciando sincronización de {base_data_type}",
        {"data_type": data_type, "registros_recibidos": len(processed_data)}
    )

    if base_data_type not in model_mapping:
        log_ubibot_event(
            "SYNC_ERROR",
            f"Tipo de dato desconocido: {base_data_type}",
            {"data_type": data_type},
            level="ERROR"
        )
        return

    model = model_mapping[base_data_type]

    if base_data_type == 'channels':
        db.session.query(model).delete()
        data_dict = processed_data.to_dict(orient='records')
        new_data = []

        # Log muestra de datos entrantes
        sample_data = data_dict[:3] if len(data_dict) > 3 else data_dict
        log_ubibot_event(
            "CHANNELS_DATA_SAMPLE",
            "Muestra de canales a insertar",
            {
                "total_canales": len(data_dict),
                "muestra": sample_data,
                "campos": list(data_dict[0].keys()) if data_dict else []
            }
        )

        for item in data_dict:
            instance = model(**item)
            db.session.add(instance)
            new_data.append(item)
        try:
            db.session.commit()
            log_ubibot_event(
                "CHANNELS_SYNC_SUCCESS",
                f"Canales sincronizados correctamente",
                {
                    "registros_insertados": len(new_data),
                    "channel_ids": [item.get('channel_id') for item in new_data[:10]]
                }
            )
        except IntegrityError as e:
            db.session.rollback()
            log_ubibot_event(
                "CHANNELS_SYNC_ERROR",
                "Error de integridad al insertar canales",
                {"error": str(e), "tipo": "IntegrityError"},
                level="ERROR"
            )
        except SQLAlchemyError as e:
            db.session.rollback()
            log_ubibot_event(
                "CHANNELS_SYNC_ERROR",
                "Error de base de datos al insertar canales",
                {"error": str(e), "tipo": "SQLAlchemyError"},
                level="ERROR"
            )

    elif base_data_type == 'summary':
        data_dict = processed_data.to_dict(orient='records')
        cleaned_data_dict = clean_data(data_dict)

        log_ubibot_event(
            "SUMMARY_DATA_RECEIVED",
            "Datos de resumen recibidos",
            {
                "registros_originales": len(data_dict),
                "registros_limpios": len(cleaned_data_dict) if cleaned_data_dict else 0
            }
        )

        if not cleaned_data_dict:
            log_ubibot_event(
                "SUMMARY_NO_DATA",
                "No hay registros nuevos para insertar",
                {"motivo": "cleaned_data_dict vacío"},
                level="WARNING"
            )
            return

        try:
            select_query = """
            SELECT id, created_at, channel_id, date, hour
            FROM ubi_channel_summary
            WHERE created_at >= CURRENT_DATE - INTERVAL '11 days';
            """
            existing_records = db.session.execute(text(select_query)).fetchall()
            # row[1] = created_at, row[2] = channel_id
            # Usar string ISO para comparación consistente
            existing_records_set = set()
            for row in existing_records:
                created_at = row[1]
                created_at_str = created_at.strftime('%Y-%m-%dT%H:%M:%S') if hasattr(created_at, 'strftime') else str(created_at)
                existing_records_set.add((created_at_str, str(row[2])))

            log_ubibot_event(
                "SUMMARY_EXISTING_CHECK",
                "Verificación de registros existentes",
                {"registros_existentes_11_dias": len(existing_records)}
            )
        except Exception as e:
            log_ubibot_event(
                "SUMMARY_QUERY_ERROR",
                "Error al consultar registros existentes",
                {"error": str(e)},
                level="ERROR"
            )
            return

        # Filtrar datos que no existen aún
        filtered_data = []
        for item in cleaned_data_dict:
            created_at = item['created_at']
            # Normalizar a string ISO para comparación
            if hasattr(created_at, 'strftime'):
                created_at_str = created_at.strftime('%Y-%m-%dT%H:%M:%S')
            elif hasattr(created_at, 'isoformat'):
                created_at_str = created_at.isoformat()
            else:
                created_at_str = str(created_at)

            key = (created_at_str, str(item['channel_id']))
            if key not in existing_records_set:
                filtered_data.append(item)

        if not filtered_data:
            log_ubibot_event(
                "SUMMARY_NO_NEW_DATA",
                "No hay registros nuevos después del filtrado",
                {
                    "registros_filtrados": len(cleaned_data_dict),
                    "registros_existentes": len(existing_records_set)
                },
                level="WARNING"
            )
            return

        # Log detallado de datos a insertar
        channels_en_batch = list(set(item.get('channel_id') for item in filtered_data))
        fechas_en_batch = list(set(str(item.get('date')) for item in filtered_data))

        log_ubibot_event(
            "SUMMARY_INSERT_PREVIEW",
            "Preparando inserción de resúmenes",
            {
                "registros_a_insertar": len(filtered_data),
                "canales_afectados": channels_en_batch[:10],
                "fechas": sorted(fechas_en_batch)[:5],
                "muestra": filtered_data[:3] if len(filtered_data) > 3 else filtered_data
            }
        )

        # INSERT simple - el filtrado previo ya elimina duplicados
        insert_statement = """
        INSERT INTO ubi_channel_summary (id, created_at, channel_id, date, hour)
        VALUES (:id, :created_at, :channel_id, :date, :hour);
        """

        try:
            for item in filtered_data:
                db.session.execute(text(insert_statement), item)
            db.session.commit()

            log_ubibot_event(
                "SUMMARY_SYNC_SUCCESS",
                "Resúmenes insertados correctamente",
                {
                    "registros_insertados": len(filtered_data),
                    "canales": channels_en_batch,
                    "rango_fechas": {
                        "desde": min(fechas_en_batch) if fechas_en_batch else None,
                        "hasta": max(fechas_en_batch) if fechas_en_batch else None
                    }
                }
            )
        except IntegrityError as e:
            db.session.rollback()
            log_ubibot_event(
                "SUMMARY_SYNC_ERROR",
                "Error de integridad al insertar resúmenes",
                {"error": str(e), "tipo": "IntegrityError"},
                level="ERROR"
            )
        except DataError as e:
            db.session.rollback()
            log_ubibot_event(
                "SUMMARY_SYNC_ERROR",
                "Error de datos al insertar resúmenes",
                {"error": str(e), "tipo": "DataError"},
                level="ERROR"
            )
        except SQLAlchemyError as e:
            db.session.rollback()
            log_ubibot_event(
                "SUMMARY_SYNC_ERROR",
                "Error de base de datos al insertar resúmenes",
                {"error": str(e), "tipo": "SQLAlchemyError"},
                level="ERROR"
            )

def manage_fields_ubi(df, batch_size=2000):
    """
    Inserta/actualiza campos de Ubibot en la base de datos.
    Optimizado: batch_size aumentado a 2000 y commit al final.
    """
    log_ubibot_event(
        "FIELDS_SYNC_START",
        "Iniciando sincronización de campos Ubibot",
        {"registros_recibidos": len(df), "batch_size": batch_size}
    )

    try:
        # Consultar registros existentes con su count para decidir si actualizar
        select_query = """
        SELECT created_at, channel_id, name, count
        FROM ubi_channels_fields
        WHERE created_at >= CURRENT_DATE - INTERVAL '11 days';
        """
        result = db.session.execute(text(select_query))
        existing_records = result.fetchall()

        # Crear diccionario para búsqueda rápida: (created_at_str, channel_id, name) -> count
        existing_dict = {}
        for row in existing_records:
            created_at = row[0]
            # Convertir a string ISO para comparación consistente
            created_at_str = created_at.strftime('%Y-%m-%dT%H:%M:%S') if hasattr(created_at, 'strftime') else str(created_at)
            key = (created_at_str, str(row[1]), row[2])  # created_at_str, channel_id, name
            existing_dict[key] = row[3]  # count

        log_ubibot_event(
            "FIELDS_EXISTING_CHECK",
            "Verificación de campos existentes",
            {"registros_existentes_11_dias": len(existing_records)}
        )
    except Exception as e:
        log_ubibot_event(
            "FIELDS_QUERY_ERROR",
            "Error al consultar campos existentes",
            {"error": str(e)},
            level="ERROR"
        )
        return

    # Limpieza de datos
    registros_antes = len(df)
    df = df.dropna(subset=['channel_id', 'created_at'])
    registros_despues = len(df)
    df['avg'] = df['avg'].fillna(0)
    df['count'] = df['count'].fillna(0)
    df['min'] = df['min'].fillna(0)
    df['max'] = df['max'].fillna(0)

    log_ubibot_event(
        "FIELDS_DATA_CLEANED",
        "Datos limpiados y preparados",
        {
            "registros_originales": registros_antes,
            "registros_validos": registros_despues,
            "registros_eliminados": registros_antes - registros_despues
        }
    )

    data_dicts = df.to_dict(orient='records')
    total_records = len(data_dicts)

    if total_records == 0:
        log_ubibot_event(
            "FIELDS_NO_DATA",
            "No hay campos para procesar",
            {},
            level="WARNING"
        )
        return

    # Separar registros nuevos de los que necesitan actualización
    records_to_insert = []
    records_to_update = []

    for item in data_dicts:
        created_at = item['created_at']
        # Convertir a string ISO para comparación consistente (timestamps ya vienen sin timezone)
        if hasattr(created_at, 'strftime'):
            created_at_str = created_at.strftime('%Y-%m-%dT%H:%M:%S')
        elif hasattr(created_at, 'isoformat'):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = str(created_at)

        key = (created_at_str, str(item['channel_id']), item['name'])
        if key in existing_dict:
            # Ya existe - solo actualizar si count < 12
            if existing_dict[key] is not None and existing_dict[key] < 12:
                records_to_update.append(item)
        else:
            # No existe - insertar
            records_to_insert.append(item)

    # Estadísticas de los datos
    channels_unicos = df['channel_id'].nunique() if 'channel_id' in df.columns else 0
    campos_unicos = df['name'].unique().tolist() if 'name' in df.columns else []
    fechas_unicas = df['date'].unique().tolist() if 'date' in df.columns else []

    log_ubibot_event(
        "FIELDS_INSERT_PREVIEW",
        "Preparando inserción/actualización de campos",
        {
            "total_registros": total_records,
            "registros_nuevos": len(records_to_insert),
            "registros_a_actualizar": len(records_to_update),
            "registros_omitidos": total_records - len(records_to_insert) - len(records_to_update),
            "canales_unicos": channels_unicos,
            "tipos_campo": campos_unicos[:10] if len(campos_unicos) > 10 else campos_unicos,
            "fechas": [str(f) for f in sorted(fechas_unicas)[:5]] if fechas_unicas else []
        }
    )

    insert_statement = """
    INSERT INTO ubi_channels_fields (created_at, channel_id, name, avg, count, min, max, date, hour, summary_id)
    VALUES (:created_at, :channel_id, :name, :avg, :count, :min, :max, :date, :hour, :summary_id);
    """

    update_statement = """
    UPDATE ubi_channels_fields
    SET avg = :avg, count = :count, min = :min, max = :max
    WHERE created_at = :created_at AND channel_id = :channel_id AND name = :name;
    """

    try:
        inserted_count = 0
        updated_count = 0

        # Insertar nuevos registros en lotes
        if records_to_insert:
            total_insert_batches = (len(records_to_insert) + batch_size - 1) // batch_size
            log_ubibot_event(
                "FIELDS_INSERT_START",
                "Iniciando inserción de registros nuevos",
                {"total_registros": len(records_to_insert), "lotes": total_insert_batches}
            )

            for i in range(0, len(records_to_insert), batch_size):
                batch = records_to_insert[i:i + batch_size]
                for item in batch:
                    db.session.execute(text(insert_statement), item)
                    inserted_count += 1

        # Actualizar registros existentes en lotes
        if records_to_update:
            total_update_batches = (len(records_to_update) + batch_size - 1) // batch_size
            log_ubibot_event(
                "FIELDS_UPDATE_START",
                "Iniciando actualización de registros existentes",
                {"total_registros": len(records_to_update), "lotes": total_update_batches}
            )

            for i in range(0, len(records_to_update), batch_size):
                batch = records_to_update[i:i + batch_size]
                for item in batch:
                    db.session.execute(text(update_statement), item)
                    updated_count += 1

        db.session.commit()

        log_ubibot_event(
            "FIELDS_SYNC_SUCCESS",
            "Campos sincronizados correctamente",
            {
                "registros_insertados": inserted_count,
                "registros_actualizados": updated_count,
                "canales_actualizados": channels_unicos,
                "tipos_campo": campos_unicos
            }
        )

    except IntegrityError as e:
        db.session.rollback()
        log_ubibot_event(
            "FIELDS_SYNC_ERROR",
            "Error de integridad al insertar campos",
            {"error": str(e), "tipo": "IntegrityError", "registros_afectados": total_records},
            level="ERROR"
        )
    except Exception as e:
        db.session.rollback()
        log_ubibot_event(
            "FIELDS_SYNC_ERROR",
            "Error inesperado al insertar campos",
            {"error": str(e), "tipo": type(e).__name__},
            level="ERROR"
        )