import requests
import datetime
from .data_processing import process_data_wc_farms_zones, process_data_irrigation, process_data_real_irrigation, process_data_measures, process_sensor_data
import os
import time

api_key = os.getenv('API_KEY')

endpoints_config = {
    "farms": {
        "url": "https://api.wiseconn.com/farms",
    },
    "sensor_data": {
        "url_template": "https://api.wiseconn.com/measures/{sensor_id}/data",
        "process_function": process_sensor_data
    }
}

def fetch_data_with_retries(url, headers, params, retries=3, delay=5):

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 500:
                print(f"Error 500: Internal Server Error for {url}. Retrying {attempt + 1}/{retries}...")
                time.sleep(delay)  
            else:
                print(f"Error fetching data from {url}: {e}")
                return None
    print(f"Failed to fetch data from {url} after {retries} attempts.")
    return None

def fetch_data(endpoint_key, sensor_id=None):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1) 
    config = endpoints_config[endpoint_key]
    headers = {"api_key": api_key}
    params = config.get("params", {})
    
    if "irrigations" in endpoint_key or "realirrigations" in endpoint_key or endpoint_key == "sensor_data":
        params["initTime"] = yesterday.strftime("%Y-%m-%d")
        params["endTime"] = today.strftime("%Y-%m-%d") 

    if endpoint_key == "sensor_data" and sensor_id:
        url = config["url_template"].format(sensor_id=sensor_id)
        response = fetch_data_with_retries(url, headers, params)
    else:
        response = fetch_data_with_retries(config["url"], headers, params)
    
    return response

def generate_farm_endpoints(farms_data):

    for farm in farms_data:
        farmid = farm['id']
        
        endpoints_config[f"zones_{farmid}"] = {
            "url": f"https://api.wiseconn.com/farms/{farmid}/zones",
            "process_function": process_data_wc_farms_zones
        }
        endpoints_config[f"irrigations_{farmid}"] = {
            "url": f"https://api.wiseconn.com/farms/{farmid}/irrigations",
            "process_function": lambda data, farm_id=farmid: process_data_irrigation(data, farm_id)
        }
        endpoints_config[f"realirrigations_{farmid}"] = {
            "url": f"https://api.wiseconn.com/farms/{farmid}/realIrrigations",
            "process_function": lambda data, farm_id=farmid: process_data_real_irrigation(data, farm_id)
        }
        endpoints_config[f"measures_{farmid}"] = {
            "url": f"https://api.wiseconn.com/farms/{farmid}/measures",
            "process_function": process_data_measures
        }

def run_fetch_process():
    results = []
    status_wiseconn = "Success"
    combined_data = []

    try:
        
        farms_data = fetch_data("farms")
        if farms_data:
            generate_farm_endpoints(farms_data) 

        
        for measure_type in [key for key in endpoints_config.keys() if key.startswith("measures_")]:
            measures_data = fetch_data(measure_type)
            if measures_data:
                processed_measures = endpoints_config[measure_type]["process_function"](measures_data)
                unique_ids = processed_measures["unique_ids"]
                farmId = measure_type.split('_')[-1]

                for sensor_id in unique_ids:
                    sensor_data = fetch_data("sensor_data", sensor_id)
                    if sensor_data:
                        processed_sensor_data = endpoints_config["sensor_data"]["process_function"](sensor_data, farmId)
                        matching_measure = next(
                            (item for item in processed_measures["processed_items"] if item["sensor_id"] == sensor_id),
                            None
                        )
                        if matching_measure:
                            # Use yesterday's value — sensor_data returns [yesterday, today].
                            # today's value is the partial intraday accumulation (resets at 00:00 UTC).
                            # yesterday's value is the fully closed daily accumulation.
                            yesterday_date = datetime.date.today() - datetime.timedelta(days=1)
                            yesterday_value = next(
                                (v for v in processed_sensor_data["values"]
                                 if v.get("date") == yesterday_date),
                                None
                            )
                            # Fall back to last available if yesterday not found
                            target_value = yesterday_value or (
                                processed_sensor_data["values"][-1]
                                if processed_sensor_data["values"] else None
                            )
                            matching_measure["values"] = target_value["value"] if target_value else None
                            matching_measure["created_at"] = target_value.get("created_at", None) if target_value else None
                            matching_measure["date"] = target_value.get("date", None) if target_value else None
                            matching_measure["hour"] = target_value.get("hour", None) if target_value else None
                            matching_measure["farm_id"] = farmId
                            combined_data.append(matching_measure)

        if combined_data:
            results.append((combined_data, "combined_measures_sensor_data"))

        for key in [key for key in endpoints_config.keys() if key.startswith(("zones_", "irrigations_", "realirrigations_"))]:
            data = fetch_data(key)
            if data:
                processed_data = endpoints_config[key]["process_function"](data)
                results.append((processed_data, key))
            else:
                print(f"No data for {key}")

    except Exception as e:
        status_wiseconn = f'Failed: {e}'
        print(f"Error during fetch process: {e}")

    return results, status_wiseconn
