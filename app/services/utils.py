# Incorporates extra useful functions

import pandas as pd
import uuid
import pytz
from datetime import datetime
import logging
import sys
import json

# Configurar logger para Google Cloud
logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log_utils_event(event_type, message, data=None, level="INFO"):
    """Log estructurado para Google Cloud Logging."""
    log_entry = {
        "service": "utils",
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
    elif level == "DEBUG":
        logger.debug(log_message)
    else:
        logger.info(log_message)

def convert_to_chilean_time(utc_datetime):
    chile_tz = pytz.timezone('America/Santiago')
    if isinstance(utc_datetime, str):
        utc_datetime = datetime.strptime(utc_datetime, '%Y-%m-%d %H:%M:%S')
    chilean_time = utc_datetime.replace(tzinfo=pytz.UTC).astimezone(chile_tz)
    return chilean_time

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

def create_channel_sensor_mapping(df):
    channel_mapping = {}
    for _, row in df.iterrows():
        channel_id = int(row['channel_id'])
        if channel_id not in channel_mapping:
            channel_mapping[channel_id] = {}
        for i in range(1, 16):
            field_name = f'field{i}'
            sensor_name = row[field_name]
            if pd.notna(sensor_name):
                channel_mapping[channel_id][field_name] = sensor_name
    return channel_mapping

def create_final_dataframe(dict_channels, df_summary):
    rows = []
    campos_faltantes = {}  # Agrupar campos faltantes por channel_id

    for channel_id, fields in dict_channels.items():
        df_channel = df_summary[df_summary['channel_id'] == channel_id]
        for field, sensor_name in fields.items():
            avg_col = f"{field}_avg"
            count_col = f"{field}_count"
            min_col = f"{field}_min"
            max_col = f"{field}_max"
            if avg_col in df_channel.columns and count_col in df_channel.columns and min_col in df_channel.columns and max_col in df_channel.columns:
                for _, row in df_channel.iterrows():
                    new_row = {
                        'summary_id': row['id'],
                        'channel_id': channel_id,
                        'created_at': row['created_at'],
                        'date': row['date'],
                        'hour': row['hour'],
                        'name': sensor_name,
                        'avg': row[avg_col],
                        'count': row[count_col],
                        'min': row[min_col],
                        'max': row[max_col]
                    }
                    rows.append(new_row)
            else:
                # Agrupar campos faltantes en lugar de imprimir uno por uno
                if channel_id not in campos_faltantes:
                    campos_faltantes[channel_id] = []
                campos_faltantes[channel_id].append(field)

    final_df = pd.DataFrame(rows)

    # Log resumen de campos faltantes (solo si hay)
    if campos_faltantes:
        log_utils_event(
            "FIELDS_MISSING_SUMMARY",
            "Resumen de campos sin datos en df_summary",
            {
                "canales_afectados": len(campos_faltantes),
                "detalle": {str(k): v for k, v in list(campos_faltantes.items())[:5]},
                "nota": "Esto es normal - no todos los canales tienen 15 sensores"
            },
            level="DEBUG"
        )

    log_utils_event(
        "FINAL_DATAFRAME_CREATED",
        "DataFrame final creado",
        {
            "total_filas": len(final_df),
            "canales_procesados": len(dict_channels),
            "canales_con_campos_faltantes": len(campos_faltantes)
        }
    )

    return final_df
