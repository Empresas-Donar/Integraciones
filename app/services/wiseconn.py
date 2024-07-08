# Controls access to the wiseconn and ubibot APIs and returns the result of this access and call cleanup functions.

import requests
import datetime
from .data_processing import process_data_wc_farms_zones, process_data_irrigation, process_data_real_irrigation
import os

endpoints_config = {
    "zones": {
        "url": "https://api.wiseconn.com/farms/14245/zones",
        "process_function": process_data_wc_farms_zones
    },
    "irrigations": {
        "url": "https://api.wiseconn.com/farms/14245/irrigations",
        "process_function": process_data_irrigation
    },
    'realirrigations': {
        "url": "https://api.wiseconn.com/farms/14245/realIrrigations",
        "process_function": process_data_real_irrigation
    }
}
api_key = os.getenv('API_KEY')  

def fetch_data(endpoint_key):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    config = endpoints_config[endpoint_key]
    headers = {"api_key": api_key}  
    params = config.get("params", {})
    if endpoint_key in ["irrigations",'realirrigations'] :
        params["initTime"] = yesterday.strftime("%Y-%m-%d")
        params["endTime"] = today.strftime("%Y-%m-%d")
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
    status_ubibot = "Failed"
    try:
        for key in endpoints_config:
            data = fetch_data(key)
            if data:  
                processed_data = endpoints_config[key]["process_function"](data)
                results.append((processed_data, key))  
    except Exception as e:
        status_wiseconn = f'Failed: {e}'
    try:
        response = requests.get("https://api.ubibot.com/status")
        if response.status_code == 200:
            status_ubibot = "Success"
        else:
            status_ubibot = "Failed"
    except Exception as e:
        status_ubibot = f'Failed: {e}'
    return results, status_wiseconn