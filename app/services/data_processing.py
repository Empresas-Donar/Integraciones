# Data processing and cleaning for each table

import pandas as pd
import uuid
from datetime import datetime
from app.services.utils import try_parsing_date

raw_data_ubi_channels = None
raw_df_summary = pd.DataFrame()

def process_data_wc_farms_zones(data_wc_farms_zones):
    df_wc_farms_zones = pd.DataFrame(data_wc_farms_zones)
    df_wc_farms_zones[['irrigation_max', 'irrigation_min', 'irrigation_avg', 'irrigation_std']] = df_wc_farms_zones['irrigationScheduleStats'].apply(pd.Series)[['max', 'min', 'avg', 'std']]
    df_wc_farms_zones.drop('irrigationScheduleStats', axis = 1, inplace= True)
    df_wc_farms_zones['bounds'] = df_wc_farms_zones['polygon'].apply(lambda x: x['bounds'] if pd.notna(x) and 'bounds' in x else None)
    df_bounds_farms_zones = df_wc_farms_zones['bounds'].apply(pd.Series)
    df_wc_farms_zones = pd.concat([df_wc_farms_zones, df_bounds_farms_zones], axis=1)
    df_wc_farms_zones['southWest_lng'] = df_wc_farms_zones['southWest'].apply(lambda x: x['lng'] if isinstance(x, dict) else None)
    df_wc_farms_zones['southWest_lat'] = df_wc_farms_zones['southWest'].apply(lambda x: x['lat'] if isinstance(x, dict) else None)
    df_wc_farms_zones['northEast_lng'] = df_wc_farms_zones['northEast'].apply(lambda x: x['lng'] if isinstance(x, dict) else None)
    df_wc_farms_zones['northEast_lat'] = df_wc_farms_zones['northEast'].apply(lambda x: x['lat'] if isinstance(x, dict) else None)
    df_wc_farms_zones.drop(["bounds", "southWest", "northEast", "polygon" , "areaUnit", "unitTheoreticalFlow", "metadata", "BFPressureId", "onlyMonitoring", "allowPumpSelection"], axis = 1, inplace = True)
    df_wc_farms_zones.rename(columns = {"area" : "area_m2", "theoreticalFlow" : "theoreticalflowm3h", "farmId": "farmid", "pumpSystemId": "pumpsystemid", "humidityRetention": "humidityretention", "criticalPoint1": "criticalpoint1", "criticalPoint2": "criticalpoint2", "criticalPoint3": "criticalpoint3", "criticalPoint4": "criticalpoint4", "soilMode": "soilmode", "pumpIds": "pumpids", "predefinedPumps": "predefinedpumps", "southWest_lng": "southwest_lng", "southWest_lat": "southwest_lat", "northEast_lng": "northeast_lng", "northEast_lat": "northeast_lat"}, inplace = True)
    df_wc_farms_zones['created_at'] = pd.Timestamp.now()
    df_wc_farms_zones['date'] = df_wc_farms_zones['created_at'].dt.date
    df_wc_farms_zones['hour'] = df_wc_farms_zones['created_at'].dt.time
    return df_wc_farms_zones
def process_data_irrigation(data_wc_farms_irrigation):
    df_wc_farms_irrigation = pd.DataFrame(data_wc_farms_irrigation)
    df_wc_farms_irrigation.rename(columns = {"initTime": "inittime", "endTime": "endtime", "irrigationType": "irrigationtype", "pumpSystemId": "pumpsystemid", "pumpIds": "pumpids", "zoneId": "zoneid", "sentToNetwork": "senttonetwork", "scheduledType": "scheduledtype", "groupingName": "groupingname"}, inplace = True)
    df_wc_farms_irrigation[["volume m3" , "volume2"]] = df_wc_farms_irrigation['volume'].apply(pd.Series)[["value", "unitAbrev"]]
    df_wc_farms_irrigation[["precipitation mm" , "precipitation2"]] = df_wc_farms_irrigation['precipitation'].apply(pd.Series)[["value", "unitAbrev"]]
    df_wc_farms_irrigation[["theoricalFlow m3/h" , "th2"]] = df_wc_farms_irrigation['theoricalFlow'].apply(pd.Series)[["value", "unitAbrev"]]
    df_wc_farms_irrigation.drop(['volume', 'precipitation', 'theoricalFlow',"volume2", "precipitation2", "th2" ],axis = 1, inplace = True)
    df_wc_farms_irrigation.drop(["programmedByUser", "nutrients", 'scheduledFertigations',
       'nutricontrol', 'scheduledPhControls'], axis = 1, inplace = True)
    df_wc_farms_irrigation.rename(columns = {"volume m3": "volume_m3", "precipitation mm": "precipitation_mm", "theoricalFlow m3/h": "theoreticalflow_m3_h"} , inplace= True)
    df_wc_farms_irrigation['inittime'] = pd.to_datetime(df_wc_farms_irrigation['inittime'], errors='coerce')
    df_wc_farms_irrigation['endtime'] = df_wc_farms_irrigation['endtime'].apply(try_parsing_date)
    df_wc_farms_irrigation['delta_time'] = df_wc_farms_irrigation['endtime'] - df_wc_farms_irrigation['inittime']
    df_wc_farms_irrigation['created_at'] = pd.Timestamp.now()
    df_wc_farms_irrigation['date'] = df_wc_farms_irrigation['created_at'].dt.date
    df_wc_farms_irrigation['hour'] = df_wc_farms_irrigation['created_at'].dt.time
    return df_wc_farms_irrigation

def process_data_real_irrigation(data_wc_farms_realirrigation):
    df_wc_farms_realirrigation = pd.DataFrame(data_wc_farms_realirrigation)
    df_wc_farms_realirrigation[["volume m3" , "volume1", "volume2"]] = df_wc_farms_realirrigation['volume'].apply(pd.Series)[["value","unitName", "unitAbrev"]]
    df_wc_farms_realirrigation[["precipitation mm" , "precipitation2", "precipitation3"]] = df_wc_farms_realirrigation['precipitation'].apply(pd.Series)[["value","unitName", "unitAbrev"]]
    df_wc_farms_realirrigation[["flow m3/h" , "th2", "th3"]] = df_wc_farms_realirrigation['flow'].apply(pd.Series)[["value","unitName", "unitAbrev"]]
    df_wc_farms_realirrigation[['instantaneousFlow m3/h' , "instantaneousFlow1", "instantaneousFlow2"]] = df_wc_farms_realirrigation['instantaneousFlow'].apply(pd.Series)[["value","unitName", "unitAbrev"]]
    df_wc_farms_realirrigation.drop(["volume1", "volume2", "precipitation2", "precipitation3", "th2", "th3","instantaneousFlow1", "instantaneousFlow2", "volume", "precipitation", "flow", "instantaneousFlow", "type", "BFPressure", "AFPressure", "instantaneousPressure", "stoppedByUser", "fertigations", "phControl", "measures", "alarms", "hydraulics"],axis = 1, inplace = True)
    df_wc_farms_realirrigation.rename(columns = {"initTime": "init_time", "endTime": "end_time", "zoneId": "zone_id", "pumpSystemId": "pump_system_id", "scheduledIrrigationId": "scheduled_irrigation_id", "volume m3": "volume_m3", "precipitation mm": "precipitation_mm", "flow m3/h": "flow_m3_h", "instantaneousFlow m3/h": "instantaneous_flow_m3_h"}, inplace = True)
    df_wc_farms_realirrigation['init_time'] = pd.to_datetime(df_wc_farms_realirrigation['init_time'], errors='coerce')
    df_wc_farms_realirrigation['end_time'] = df_wc_farms_realirrigation['end_time'].apply(try_parsing_date)
    df_wc_farms_realirrigation['delta_time'] = df_wc_farms_realirrigation['end_time'] - df_wc_farms_realirrigation['init_time']
    df_wc_farms_realirrigation['created_at'] = pd.Timestamp.now()
    df_wc_farms_realirrigation['date'] = df_wc_farms_realirrigation['created_at'].dt.date
    df_wc_farms_realirrigation['hour'] = df_wc_farms_realirrigation['created_at'].dt.time
    return df_wc_farms_realirrigation

def clean_channel_data(data_ubi_channels):

    if isinstance(data_ubi_channels, dict):
        data_ubi_channels = pd.DataFrame(data_ubi_channels['channels'])
    elif isinstance(data_ubi_channels, list):
        data_ubi_channels = pd.DataFrame(data_ubi_channels)
    global raw_data_ubi_channels
    raw_data_ubi_channels = data_ubi_channels.copy() 
    data_ubi_channels['id'] = range(1, len(data_ubi_channels) + 1)
    data_ubi_channels.replace('', None, inplace=True)
    data_ubi_channels['created_at'] = pd.Timestamp.now()
    data_ubi_channels['date'] = data_ubi_channels['created_at'].dt.date
    data_ubi_channels['hour'] = data_ubi_channels['created_at'].dt.time
    allowed_columns = [
        'id', 'channel_id', 'created_at', 'date', 'hour',  'latitude', 'longitude', 'name'
    ]
    columns_to_drop = [col for col in data_ubi_channels.columns if col not in allowed_columns]
    data_ubi_channels.drop(columns=columns_to_drop, axis=1, inplace=True)
    return data_ubi_channels

def clean_channel_data_summary(data_ubi_summary, channel_id):
    if isinstance(data_ubi_summary, list):
        data_ubi_summary = pd.json_normalize(data_ubi_summary)
    elif isinstance(data_ubi_summary, dict):
        data_ubi_summary = pd.DataFrame([data_ubi_summary])    
    if 'id' not in data_ubi_summary.columns:
        data_ubi_summary['id'] = [uuid.uuid4().hex for _ in range(len(data_ubi_summary))]
    data_ubi_summary['channel_id'] = channel_id
    data_ubi_summary.columns = data_ubi_summary.columns.str.replace('.', '_')
    if 'created_at' not in data_ubi_summary.columns:
        data_ubi_summary['created_at'] = None
    data_ubi_summary['created_at'] = pd.to_datetime(data_ubi_summary['created_at'])
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
    columns_to_drop = []
    for field in expected_fields:
        for metric in ['sum', 'sd']:
            columns_to_drop.append(f'{field}_{metric}')
    data_ubi_summary.drop(columns=[col for col in columns_to_drop if col in data_ubi_summary.columns], inplace=True)
    global raw_df_summary
    raw_df_summary = pd.concat([raw_df_summary, data_ubi_summary], ignore_index=True)
    columns_to_keep = ['id', 'channel_id', 'created_at', 'date', 'hour']
    data_ubi_summary = data_ubi_summary[columns_to_keep]

    return data_ubi_summary