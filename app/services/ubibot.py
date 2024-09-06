# Controls access to the Ubibot  APIs and returns the result of this access and call cleanup functions.

import requests
import pandas as pd
from urllib.parse import urlencode
from datetime import datetime, timedelta
import os
import time
from .data_processing import clean_channel_data, clean_channel_data_summary 

account_key = os.getenv('UBIBOT_ACCOUNT_KEY')
request_counter = 0
start_time = time.time()

endpoints_config = {
    "channels": {
        "url": "https://webapi.ubibot.com/channels",
        "process_function": clean_channel_data
    }
}

def fetch_data_ubi(endpoint_key):
    global request_counter, start_time
    config = endpoints_config[endpoint_key]
    if endpoint_key == "channels":
        url = config["url"]
        params = {'account_key': account_key}
        response = requests.get(url, params=params)
        request_counter += 1
        print(f"Fetching {url} with params {params}")
        if response.status_code == 200:
            return response.json(), endpoint_key
        else:
            print(f"Error fetching data from {config['url']}: {response.status_code}")
            return None, endpoint_key
    else:
        url = config["url"]
        today = datetime.today()
        yesterday = today - timedelta(days=10)
        params = {
            "account_key": account_key,
            "results": 5000,
            "start": yesterday.strftime('%Y-%m-%d %H:%M:%S'),
            "end": today.strftime('%Y-%m-%d %H:%M:%S')
        }
        params_encoded = urlencode(params)
        response = requests.get(f"{url}?{params_encoded}")
        request_counter += 1
        print(f"Fetching {url} with params {params}")
        if response.status_code == 200:
            data = response.json()
            if data.get("result") == "success":
                feeds = data.get('feeds', [])
                return feeds, endpoint_key
            else:
                print(f"Error: {data.get('errorCode')} - {data.get('desp')}")
        else:
            print(f"Error fetching data for {endpoint_key}: {response.status_code}")
        return None, endpoint_key 


def generate_summary_endpoints(channels_data):
    for channel in channels_data['channels']:
        channel_id = channel['channel_id']
        endpoint_key = f"summary_{channel_id}"
        endpoints_config[endpoint_key] = {
            "url": f"https://webapi.ubibot.com/channels/{channel_id}/summary",
            "process_function": clean_channel_data_summary,
            "channel_id": channel_id
        }

def runubi_fetch_process():
    global request_counter, start_time
    results = []
    status_ubibot = "Success"
    try:
        channels_data, endpoint_key = fetch_data_ubi("channels")
        if channels_data:
            process_function = endpoints_config[endpoint_key]["process_function"]
            processed_data = process_function(channels_data)
            results.append((processed_data, str(endpoint_key)))
            generate_summary_endpoints(channels_data)
        
        endpoint_keys = list(endpoints_config.keys())
        total_endpoints = len(endpoint_keys)
        
        for i in range(0, total_endpoints, 10):
            batch = endpoint_keys[i:i+10]
            for key in batch:
                if key == "channels":
                    continue
                data, endpoint_key = fetch_data_ubi(key)
                if data:
                    process_function = endpoints_config[key]["process_function"]
                    processed_data = process_function(data, endpoints_config[key]["channel_id"])
                    results.append((processed_data, str(endpoint_key)))          
            if i + 10 < total_endpoints:
                print("Sleeping for 60 seconds to avoid rate limit")
                time.sleep(60)
                request_counter = 0
                start_time = time.time()
            
    except Exception as e:
        status_ubibot = f'Failed: {e}'
    
    return results, status_ubibot
