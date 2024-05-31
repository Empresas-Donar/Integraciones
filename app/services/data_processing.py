# Data processing and cleaning for each table

import pandas as pd

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
    
    return df_wc_farms_irrigation