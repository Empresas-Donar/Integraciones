# Data processing and cleaning for each table

import pandas as pd
import uuid
from datetime import datetime
import pytz
import logging
import sys
import json

# Configurar logger para Google Cloud (stdout con formato estructurado)
logger = logging.getLogger('data_processing')
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log_processing_event(event_type, message, data=None, level="INFO"):
    """
    Log estructurado para Google Cloud Logging.
    Formato JSON amigable para filtrar en Cloud Logging.
    """
    log_entry = {
        "service": "data_processing",
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


raw_data_ubi_channels = None
raw_df_summary = pd.DataFrame()
zone_id_dict = {}

def process_data_wc_farms_zones(data_wc_farms_zones):
    log_processing_event(
        "WISECONN_ZONES_START",
        "Procesando zonas de Wiseconn",
        {"registros_recibidos": len(data_wc_farms_zones) if data_wc_farms_zones else 0}
    )

    df_wc_farms_zones = pd.DataFrame(data_wc_farms_zones)

    if 'AFPressureId' in df_wc_farms_zones.columns:
        df_wc_farms_zones.drop('AFPressureId', axis=1, inplace=True)
    if 'BFPressureId' in df_wc_farms_zones.columns:
        df_wc_farms_zones.drop('BFPressureId', axis=1, inplace=True)

    df_wc_farms_zones[['irrigation_max', 'irrigation_min', 'irrigation_avg', 'irrigation_std']] = df_wc_farms_zones['irrigationScheduleStats'].apply(pd.Series)[['max', 'min', 'avg', 'std']]
    df_wc_farms_zones.drop('irrigationScheduleStats', axis = 1, inplace= True)

    df_wc_farms_zones['bounds'] = df_wc_farms_zones['polygon'].apply(lambda x: x['bounds'] if pd.notna(x) and 'bounds' in x else None)
    df_bounds_farms_zones = df_wc_farms_zones['bounds'].apply(pd.Series)
    df_wc_farms_zones = pd.concat([df_wc_farms_zones, df_bounds_farms_zones], axis=1)

    df_wc_farms_zones['southWest_lng'] = df_wc_farms_zones['southWest'].apply(lambda x: x['lng'] if isinstance(x, dict) else None)
    df_wc_farms_zones['southWest_lat'] = df_wc_farms_zones['southWest'].apply(lambda x: x['lat'] if isinstance(x, dict) else None)
    df_wc_farms_zones['northEast_lng'] = df_wc_farms_zones['northEast'].apply(lambda x: x['lng'] if isinstance(x, dict) else None)
    df_wc_farms_zones['northEast_lat'] = df_wc_farms_zones['northEast'].apply(lambda x: x['lat'] if isinstance(x, dict) else None)

    df_wc_farms_zones.drop(["bounds", "southWest", "northEast", "polygon" , "areaUnit", "unitTheoreticalFlow", "metadata", "onlyMonitoring", "allowPumpSelection"], axis = 1, inplace = True)

    df_wc_farms_zones.rename(columns = {
        "area" : "area_m2",
        "theoreticalFlow" : "theoreticalflowm3h",
        "farmId": "farm_id",
        "pumpSystemId": "pumpsystemid",
        "humidityRetention": "humidityretention",
        "criticalPoint1": "criticalpoint1",
        "criticalPoint2": "criticalpoint2",
        "criticalPoint3": "criticalpoint3",
        "criticalPoint4": "criticalpoint4",
        "soilMode": "soilmode",
        "pumpIds": "pumpids",
        "predefinedPumps": "predefinedpumps",
        "southWest_lng": "southwest_lng",
        "southWest_lat": "southwest_lat",
        "northEast_lng": "northeast_lng",
        "northEast_lat": "northeast_lat"
    }, inplace = True)

    df_wc_farms_zones['created_at'] = pd.Timestamp.now()
    df_wc_farms_zones['date'] = df_wc_farms_zones['created_at'].dt.date
    df_wc_farms_zones['hour'] = df_wc_farms_zones['created_at'].dt.time

    # Log de zonas procesadas
    zone_ids = df_wc_farms_zones['id'].tolist() if 'id' in df_wc_farms_zones.columns else []
    farm_ids = df_wc_farms_zones['farm_id'].unique().tolist() if 'farm_id' in df_wc_farms_zones.columns else []

    log_processing_event(
        "WISECONN_ZONES_PROCESSED",
        "Zonas de Wiseconn procesadas",
        {
            "total_zonas": len(df_wc_farms_zones),
            "farm_ids": farm_ids[:10],
            "zone_ids": zone_ids[:10],
            "columnas": list(df_wc_farms_zones.columns),
            "muestra": df_wc_farms_zones.head(2).to_dict(orient='records')
        }
    )

    return df_wc_farms_zones

def process_data_irrigation(data_wc_farms_irrigation, farm_id):
    log_processing_event(
        "WISECONN_IRRIGATION_START",
        "Procesando datos de irrigación programada",
        {"farm_id": farm_id, "registros_recibidos": len(data_wc_farms_irrigation) if data_wc_farms_irrigation else 0}
    )

    df_wc_farms_irrigation = pd.DataFrame(data_wc_farms_irrigation)
    df_wc_farms_irrigation['farm_id'] = farm_id
    df_wc_farms_irrigation.rename(columns = {"initTime": "inittime", "endTime": "endtime", "irrigationType": "irrigationtype", "pumpSystemId": "pumpsystemid", "pumpIds": "pumpids", "zoneId": "zone_id", "sentToNetwork": "senttonetwork", "scheduledType": "scheduledtype", "groupingName": "groupingname"}, inplace = True)
    df_wc_farms_irrigation[["volume m3" , "volume2"]] = df_wc_farms_irrigation['volume'].apply(pd.Series)[["value", "unitAbrev"]]
    df_wc_farms_irrigation[["precipitation mm" , "precipitation2"]] = df_wc_farms_irrigation['precipitation'].apply(pd.Series)[["value", "unitAbrev"]]
    df_wc_farms_irrigation[["theoricalFlow m3/h" , "th2"]] = df_wc_farms_irrigation['theoricalFlow'].apply(pd.Series)[["value", "unitAbrev"]]
    df_wc_farms_irrigation.drop(['volume', 'precipitation', 'theoricalFlow',"volume2", "precipitation2", "th2" ],axis = 1, inplace = True)
    df_wc_farms_irrigation.drop(["programmedByUser", "nutrients", 'scheduledFertigations',
       'nutricontrol', 'scheduledPhControls'], axis = 1, inplace = True)
    df_wc_farms_irrigation.rename(columns = {"volume m3": "volume_m3", "precipitation mm": "precipitation_mm", "theoricalFlow m3/h": "theoreticalflow_m3_h"} , inplace= True)
    df_wc_farms_irrigation['created_at'] = pd.to_datetime(df_wc_farms_irrigation['inittime'])
    df_wc_farms_irrigation['date'] = df_wc_farms_irrigation['created_at'].dt.date
    df_wc_farms_irrigation['hour'] = df_wc_farms_irrigation['created_at'].dt.time
    df_wc_farms_irrigation['delta_time'] = pd.to_datetime(df_wc_farms_irrigation['endtime']) - pd.to_datetime(df_wc_farms_irrigation['inittime'])

    # Log de irrigación procesada
    zonas_afectadas = df_wc_farms_irrigation['zone_id'].unique().tolist() if 'zone_id' in df_wc_farms_irrigation.columns else []
    fechas = df_wc_farms_irrigation['date'].unique().tolist() if 'date' in df_wc_farms_irrigation.columns else []

    log_processing_event(
        "WISECONN_IRRIGATION_PROCESSED",
        "Datos de irrigación programada procesados",
        {
            "farm_id": farm_id,
            "total_registros": len(df_wc_farms_irrigation),
            "zonas_afectadas": zonas_afectadas[:10],
            "fechas": [str(f) for f in sorted(fechas)[:5]],
            "volumen_total_m3": df_wc_farms_irrigation['volume_m3'].sum() if 'volume_m3' in df_wc_farms_irrigation.columns else 0,
            "muestra": df_wc_farms_irrigation.head(2).to_dict(orient='records')
        }
    )

    return df_wc_farms_irrigation

def process_data_real_irrigation(data_wc_farms_realirrigation, farm_id):
    log_processing_event(
        "WISECONN_REAL_IRRIGATION_START",
        "Procesando datos de irrigación real",
        {"farm_id": farm_id, "registros_recibidos": len(data_wc_farms_realirrigation) if data_wc_farms_realirrigation else 0}
    )

    df_wc_farms_realirrigation = pd.DataFrame(data_wc_farms_realirrigation)
    df_wc_farms_realirrigation['farm_id'] = farm_id
    df_wc_farms_realirrigation[["volume_m3", "volume1", "volume2"]] = df_wc_farms_realirrigation['volume'].apply(pd.Series)[["value", "unitName", "unitAbrev"]]
    df_wc_farms_realirrigation[["precipitation_mm", "precipitation2", "precipitation3"]] = df_wc_farms_realirrigation['precipitation'].apply(pd.Series)[["value", "unitName", "unitAbrev"]]
    df_wc_farms_realirrigation[["flow_m3_h", "th2", "th3"]] = df_wc_farms_realirrigation['flow'].apply(pd.Series)[["value", "unitName", "unitAbrev"]]
    df_wc_farms_realirrigation[['instantaneous_flow_m3_h', "instantaneousFlow1", "instantaneousFlow2"]] = df_wc_farms_realirrigation['instantaneousFlow'].apply(pd.Series)[["value", "unitName", "unitAbrev"]]

    df_wc_farms_realirrigation.drop(["volume1", "volume2", "precipitation2", "precipitation3", "th2", "th3", "instantaneousFlow1", "instantaneousFlow2",
                                     "volume", "precipitation", "flow", "instantaneousFlow", "type", "BFPressure", "AFPressure", "instantaneousPressure",
                                     "stoppedByUser", "fertigations", "phControl", "alarms", "hydraulics"], axis=1, inplace=True)

    df_wc_farms_realirrigation.rename(columns={"initTime": "init_time", "endTime": "end_time", "zoneId": "zone_id",
                                               "pumpSystemId": "pump_system_id", "scheduledIrrigationId": "scheduled_irrigation_id"}, inplace=True)
    df_wc_farms_realirrigation['init_time'] = pd.to_datetime(df_wc_farms_realirrigation['init_time'], errors='coerce')
    df_wc_farms_realirrigation['end_time'] = pd.to_datetime(df_wc_farms_realirrigation['end_time'], errors='coerce')
    df_wc_farms_realirrigation['created_at'] = df_wc_farms_realirrigation['init_time']
    df_wc_farms_realirrigation['date'] = df_wc_farms_realirrigation['created_at'].dt.date
    df_wc_farms_realirrigation['hour'] = df_wc_farms_realirrigation['created_at'].dt.time
    df_wc_farms_realirrigation['delta_time'] = df_wc_farms_realirrigation['end_time'] - df_wc_farms_realirrigation['init_time']

    def get_pressure_measure_id(measures):
        for measure in measures:
            if measure.get('sensorType') == 'Pressure':
                return measure.get('measureId')
        return None

    df_wc_farms_realirrigation['pressure_measure_id'] = df_wc_farms_realirrigation['measures'].apply(get_pressure_measure_id)

    def fetch_pressure(measure_id, init_time, end_time):
        from .wiseconn import fetch_data
        if measure_id:
            sensor_data = fetch_data('sensor_data', measure_id)
            if sensor_data:
                df_sensor_data = pd.DataFrame(sensor_data)
                if not df_sensor_data.empty:
                    df_sensor_data['time'] = pd.to_datetime(df_sensor_data['time'])
                    df_filtered = df_sensor_data[(df_sensor_data['time'] >= init_time) & (df_sensor_data['time'] <= end_time)]

                    if not df_filtered.empty:
                        return df_filtered['value'].iloc[0]

        return None

    df_wc_farms_realirrigation['pressure'] = df_wc_farms_realirrigation.apply(
        lambda row: fetch_pressure(row['pressure_measure_id'], row['init_time'], row['end_time']), axis=1
    )
    df_wc_farms_realirrigation.drop('pressure_measure_id', axis=1, inplace=True)

    # Log de irrigación real procesada
    zonas_afectadas = df_wc_farms_realirrigation['zone_id'].unique().tolist() if 'zone_id' in df_wc_farms_realirrigation.columns else []
    fechas = df_wc_farms_realirrigation['date'].unique().tolist() if 'date' in df_wc_farms_realirrigation.columns else []

    log_processing_event(
        "WISECONN_REAL_IRRIGATION_PROCESSED",
        "Datos de irrigación real procesados",
        {
            "farm_id": farm_id,
            "total_registros": len(df_wc_farms_realirrigation),
            "zonas_afectadas": zonas_afectadas[:10],
            "fechas": [str(f) for f in sorted(fechas)[:5]],
            "volumen_total_m3": float(df_wc_farms_realirrigation['volume_m3'].sum()) if 'volume_m3' in df_wc_farms_realirrigation.columns else 0,
            "flow_promedio_m3_h": float(df_wc_farms_realirrigation['flow_m3_h'].mean()) if 'flow_m3_h' in df_wc_farms_realirrigation.columns else 0,
            "muestra": df_wc_farms_realirrigation.head(2).to_dict(orient='records')
        }
    )

    return df_wc_farms_realirrigation

def process_data_measures(data_measures):
    log_processing_event(
        "WISECONN_MEASURES_START",
        "Procesando sensores/medidas de Wiseconn",
        {"registros_recibidos": len(data_measures) if data_measures else 0}
    )

    df = pd.DataFrame(data_measures)
    df['unit'] = df['unit'].fillna('N/A')
    df_unique = df.drop_duplicates(subset=['id'])
    processed_items = df_unique[['id', 'name', 'unit', 'zoneId']].rename(columns={'id': 'sensor_id', 'zoneId': 'zone_id'}).to_dict(orient='records')
    unique_ids = df_unique['id'].tolist()

    # Agrupar por tipo de sensor
    sensor_types = df_unique['name'].value_counts().to_dict() if 'name' in df_unique.columns else {}

    log_processing_event(
        "WISECONN_MEASURES_PROCESSED",
        "Sensores procesados",
        {
            "total_sensores": len(unique_ids),
            "sensores_duplicados_removidos": len(df) - len(df_unique),
            "tipos_sensor": sensor_types,
            "zone_ids": df_unique['zoneId'].unique().tolist()[:10] if 'zoneId' in df_unique.columns else [],
            "muestra": processed_items[:3]
        }
    )

    return {
        "unique_ids": unique_ids,
        "processed_items": processed_items
    }

def process_sensor_data(data, farmId):
    log_processing_event(
        "SENSOR_DATA_START",
        "Procesando datos de sensores",
        {"farm_id": farmId, "registros_recibidos": len(data) if data else 0}
    )

    chile_tz = pytz.timezone('America/Santiago')
    processed_data = {
        "values": []
    }
    farmId_str = str(farmId)
    valores = []

    for item in data:
        if "time" in item and item["time"]:
            time_obj = pd.to_datetime(item["time"])
        else:
            time_obj = datetime.now(chile_tz)

        value = item.get("value", float('nan'))
        valores.append(value)

        processed_data["values"].append({
            "created_at": time_obj,
            "date": time_obj.date(),
            "hour": time_obj.time(),
            "value": value,
            "farm_id": farmId_str
        })

    # Calcular estadísticas de los valores
    valores_validos = [v for v in valores if pd.notna(v)]

    log_processing_event(
        "SENSOR_DATA_PROCESSED",
        "Datos de sensores procesados",
        {
            "farm_id": farmId,
            "total_registros": len(processed_data["values"]),
            "valores_validos": len(valores_validos),
            "valores_nulos": len(valores) - len(valores_validos),
            "estadisticas": {
                "min": min(valores_validos) if valores_validos else None,
                "max": max(valores_validos) if valores_validos else None,
                "promedio": sum(valores_validos) / len(valores_validos) if valores_validos else None
            },
            "muestra": processed_data["values"][:3]
        }
    )

    return processed_data

def clean_channel_data(data_ubi_channels):
    log_processing_event(
        "UBIBOT_CHANNELS_START",
        "Procesando canales de Ubibot",
        {"tipo_entrada": type(data_ubi_channels).__name__}
    )

    if isinstance(data_ubi_channels, dict):
        data_ubi_channels = pd.DataFrame(data_ubi_channels['channels'])
    elif isinstance(data_ubi_channels, list):
        data_ubi_channels = pd.DataFrame(data_ubi_channels)

    global raw_data_ubi_channels
    raw_data_ubi_channels = data_ubi_channels.copy()
    data_ubi_channels['id'] = range(1, len(data_ubi_channels) + 1)
    data_ubi_channels.replace('', None, inplace=True)
    chile_tz = pytz.timezone('America/Santiago')
    current_time_in_chile = datetime.now(chile_tz)
    data_ubi_channels['created_at'] = current_time_in_chile
    data_ubi_channels['date'] = data_ubi_channels['created_at'].dt.date
    data_ubi_channels['hour'] = data_ubi_channels['created_at'].dt.time
    allowed_columns = [
        'id', 'channel_id', 'created_at', 'date', 'hour',  'latitude', 'longitude', 'name', 'net'
    ]
    columns_to_drop = [col for col in data_ubi_channels.columns if col not in allowed_columns]
    data_ubi_channels.drop(columns=columns_to_drop, axis=1, inplace=True)

    # Log de canales procesados
    channel_ids = data_ubi_channels['channel_id'].tolist() if 'channel_id' in data_ubi_channels.columns else []
    nombres = data_ubi_channels['name'].tolist() if 'name' in data_ubi_channels.columns else []

    log_processing_event(
        "UBIBOT_CHANNELS_PROCESSED",
        "Canales de Ubibot procesados",
        {
            "total_canales": len(data_ubi_channels),
            "channel_ids": channel_ids,
            "nombres": nombres,
            "columnas_eliminadas": columns_to_drop,
            "muestra": data_ubi_channels.head(3).to_dict(orient='records')
        }
    )

    return data_ubi_channels

def clean_channel_data_summary(data_ubi_summary, channel_id):
    log_processing_event(
        "UBIBOT_SUMMARY_START",
        "Procesando resumen de canal Ubibot",
        {
            "channel_id": channel_id,
            "tipo_entrada": type(data_ubi_summary).__name__,
            "registros_recibidos": len(data_ubi_summary) if isinstance(data_ubi_summary, (list, dict)) else 0
        }
    )

    if channel_id is None:
        log_processing_event(
            "UBIBOT_SUMMARY_SKIP",
            "Channel ID nulo, saltando procesamiento",
            {},
            level="WARNING"
        )
        return

    if isinstance(data_ubi_summary, list):
        data_ubi_summary = pd.json_normalize(data_ubi_summary)
    elif isinstance(data_ubi_summary, dict):
        data_ubi_summary = pd.DataFrame([data_ubi_summary])

    if data_ubi_summary.empty:
        log_processing_event(
            "UBIBOT_SUMMARY_EMPTY",
            "DataFrame vacío después de normalización",
            {"channel_id": channel_id},
            level="WARNING"
        )
        return data_ubi_summary

    if 'id' not in data_ubi_summary.columns:
        data_ubi_summary['id'] = [uuid.uuid4().hex for _ in range(len(data_ubi_summary))]

    data_ubi_summary['channel_id'] = channel_id
    data_ubi_summary.columns = data_ubi_summary.columns.str.replace('.', '_')

    data_ubi_summary['created_at'] = pd.to_datetime(data_ubi_summary['created_at'], utc=True)
    data_ubi_summary['created_at'] = data_ubi_summary['created_at'].dt.tz_convert('America/Santiago')
    # Quitar timezone para que PostgreSQL guarde el valor tal cual (hora de Chile)
    # sin hacer conversiones adicionales a la zona horaria del servidor
    data_ubi_summary['created_at'] = data_ubi_summary['created_at'].dt.tz_localize(None)

    tiene_timezone = pd.api.types.is_datetime64tz_dtype(data_ubi_summary['created_at'])
    log_processing_event(
        "UBIBOT_SUMMARY_TIMEZONE",
        "Verificación de zona horaria",
        {"channel_id": channel_id, "tiene_timezone": tiene_timezone}
    )

    data_ubi_summary['date'] = data_ubi_summary['created_at'].dt.date
    data_ubi_summary['hour'] = data_ubi_summary['created_at'].dt.time

    expected_fields = [f'field{n}' for n in range(1, 16)]
    metrics = ['avg', 'count', 'min', 'max']

    for field in expected_fields:
        if field not in data_ubi_summary.columns:
            for metric in metrics:
                column_name = f'{field}_{metric}'
                if column_name not in data_ubi_summary.columns:
                    data_ubi_summary[column_name] = None

    columns_to_drop = [f'{field}_{metric}' for field in expected_fields for metric in ['sum', 'sd']]
    data_ubi_summary.drop(columns=[col for col in columns_to_drop if col in data_ubi_summary.columns], inplace=True)

    registros_antes = len(data_ubi_summary)
    data_ubi_summary = data_ubi_summary.dropna(subset=['channel_id', 'created_at'])
    registros_despues = len(data_ubi_summary)

    if registros_antes != registros_despues:
        log_processing_event(
            "UBIBOT_SUMMARY_CLEANUP",
            "Registros eliminados por valores nulos",
            {
                "channel_id": channel_id,
                "registros_antes": registros_antes,
                "registros_despues": registros_despues,
                "eliminados": registros_antes - registros_despues
            },
            level="WARNING"
        )

    global raw_df_summary

    data_ubi_summary = data_ubi_summary.dropna(how='all', axis=1)

    if data_ubi_summary['channel_id'].isna().all():
        log_processing_event(
            "UBIBOT_SUMMARY_ERROR",
            "channel_id vacío o solo NaN",
            {"channel_id": channel_id},
            level="ERROR"
        )
        raise ValueError("'channel_id' está vacío o contiene solo NaN antes de concatenar.")

    raw_df_summary = pd.concat([raw_df_summary, data_ubi_summary], ignore_index=True, sort=False)
    columns_to_keep = ['id', 'channel_id', 'created_at', 'date', 'hour']
    data_ubi_summary = data_ubi_summary[columns_to_keep]

    # Log resumen procesado
    fechas = data_ubi_summary['date'].unique().tolist() if 'date' in data_ubi_summary.columns else []

    log_processing_event(
        "UBIBOT_SUMMARY_PROCESSED",
        "Resumen de canal Ubibot procesado",
        {
            "channel_id": channel_id,
            "total_registros": len(data_ubi_summary),
            "fechas": [str(f) for f in sorted(fechas)[:5]],
            "rango_fechas": {
                "desde": str(min(fechas)) if fechas else None,
                "hasta": str(max(fechas)) if fechas else None
            },
            "raw_df_summary_total": len(raw_df_summary),
            "muestra": data_ubi_summary.head(3).to_dict(orient='records')
        }
    )

    return data_ubi_summary
