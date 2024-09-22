# Controls access to the wiseconn and ubibot APIs and returns the result of this access and call cleanup functions.

import requests
import datetime
from .data_processing import process_data_wc_farms_zones, process_data_irrigation, process_data_real_irrigation, process_data_measures, process_sensor_data
import os

endpoints_config = {
    "zones": {
        "url": "https://api.wiseconn.com/farms/14245/zones",
        "process_function": process_data_wc_farms_zones
    },
    "zones_imaipo": {
        "url": "https://api.wiseconn.com/farms/60544/zones",
        "process_function": process_data_wc_farms_zones
    },
    "irrigations": {
        "url": "https://api.wiseconn.com/farms/14245/irrigations",
        "process_function": process_data_irrigation
    },
    "irrigations_imaipo": {
        "url": "https://api.wiseconn.com/farms/60544/irrigations",
        "process_function": process_data_irrigation
    },
    'realirrigations': {
        "url": "https://api.wiseconn.com/farms/14245/realIrrigations",
        "process_function": process_data_real_irrigation
    },
    'realirrigations_imaipo': {
        "url": "https://api.wiseconn.com/farms/60544/realIrrigations",
        "process_function": process_data_real_irrigation
    },
    "measures": {
        "url": "https://api.wiseconn.com/farms/14245/measures",
        "process_function": process_data_measures
    },
    "measures_imaipo": {
        "url": "https://api.wiseconn.com/farms/60544/measures",
        "process_function": process_data_measures
    },
    "sensor_data": {
        "url_template": "https://api.wiseconn.com/measures/{sensor_id}/data",
        "process_function": process_sensor_data
    }
}
api_key = os.getenv('API_KEY')  

def fetch_data(endpoint_key, sensor_id=None):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    config = endpoints_config[endpoint_key]
    headers = {"api_key": api_key}  
    params = config.get("params", {})
    if endpoint_key in ["irrigations", "irrigations_imaipo", "realirrigations", "realirrigations_imaipo", "sensor_data"]:
        params["initTime"] = yesterday.strftime("%Y-%m-%d")
        params["endTime"] = today.strftime("%Y-%m-%d")
    if endpoint_key == "sensor_data" and sensor_id:
        url = config["url_template"].format(sensor_id=sensor_id)
        response = requests.get(url, headers=headers, params=params)
    else:
        response = requests.get(config["url"], headers=headers, params=params)
    try:
        response.raise_for_status()  
        return response.json()  
    except requests.HTTPError as e:   
        print(f"Error fetching data from {config['url']}: {e}")
        return None  

def run_fetch_process():
    results = []
    status_wiseconn = "Success"
    combined_data = []

    try:
        
        for measure_type in ["measures", "measures_imaipo"]:
            measures_data = fetch_data(measure_type) 
            if measures_data:
                processed_measures = endpoints_config[measure_type]["process_function"](measures_data)
                unique_ids = processed_measures["unique_ids"]
                
                for sensor_id in unique_ids:
                    sensor_data = fetch_data("sensor_data", sensor_id)
                    if sensor_data:
                        processed_sensor_data = endpoints_config["sensor_data"]["process_function"](sensor_data)
                        matching_measure = next(
                            (item for item in processed_measures["processed_items"] if item["sensor_id"] == sensor_id), 
                            None
                        )
                        if matching_measure:
                            first_value = (
                                processed_sensor_data["values"][0]["value"]
                                if processed_sensor_data["values"]
                                else None
                            )
                            matching_measure["values"] = first_value
                            matching_measure["created_at"] = processed_sensor_data["values"][0].get("created_at", None)
                            matching_measure["date"] = processed_sensor_data["values"][0].get("date", None)
                            matching_measure["hour"] = processed_sensor_data["values"][0].get("hour", None)
                            matching_measure["farm_id"] = "14245" if measure_type == "measures" else "60544" 
                            combined_data.append(matching_measure)

        if combined_data:
            results.append((combined_data, "combined_measures_sensor_data"))

        for key in ["zones", "zones_imaipo", "irrigations", "irrigations_imaipo", "realirrigations", "realirrigations_imaipo"]:
            data = fetch_data(key)
            if data:
                processed_data = endpoints_config[key]["process_function"](data)
                results.append((processed_data, key))
                
    except Exception as e:
        status_wiseconn = f'Failed: {e}'
    
    return results, status_wiseconn