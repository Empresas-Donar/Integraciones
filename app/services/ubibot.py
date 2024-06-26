# Controls access to the Ubibot  APIs and returns the result of this access and call cleanup functions.

import requests
import pandas as pd
from urllib.parse import urlencode
from datetime import datetime, timedelta
import os
from .data_processing import clean_channel_data, clean_channel_data_summary 

account_key = os.getenv('UBIBOT_ACCOUNT_KEY')
endpoints_config = {
    "channels": {
        "url": "https://webapi.ubibot.com/channels",
        "process_function": clean_channel_data
    },
    "summary_67928": {
        "url": "https://webapi.ubibot.com/channels/67928/summary",
        "process_function": clean_channel_data_summary,
        "channel_id": 67928
    },
    "summary_68625": {
        "url": "https://webapi.ubibot.com/channels/68625/summary",
        "process_function": clean_channel_data_summary,
        "channel_id": 68625
    },
    "summary_71208": {
        "url": "https://webapi.ubibot.com/channels/71208/summary",
        "process_function": clean_channel_data_summary,
        "channel_id": 71208
    },
    "summary_80646": {
        "url": "https://webapi.ubibot.com/channels/80646/summary",
        "process_function": clean_channel_data_summary,
        "channel_id": 80646
    },
    "summary_80647": {
        "url": "https://webapi.ubibot.com/channels/80647/summary",
        "process_function": clean_channel_data_summary,
        "channel_id": 80647
    },
    "summary_83002": {
        "url": "https://webapi.ubibot.com/channels/83002/summary",
        "process_function": clean_channel_data_summary,
        "channel_id": 83002
    },
    "summary_83204": {
        "url": "https://webapi.ubibot.com/channels/83204/summary",
        "process_function": clean_channel_data_summary,
        "channel_id": 83204
    },
    "summary_83605": {
        "url": "https://webapi.ubibot.com/channels/83605/summary",
        "process_function": clean_channel_data_summary,
        "channel_id": 83605
    }
}

def fetch_data_ubi(endpoint_key):
    config = endpoints_config[endpoint_key]
    if endpoint_key == "channels":
        url = config["url"]
        params = {'account_key': account_key}
        response = requests.get(url, params=params)
        print(f"Fetching {url} with params {params}")
        if response.status_code == 200:
            return response.json(), endpoint_key
        else:
            print(f"Error fetching data from {config['url']}: {response.status_code}")
            return None, endpoint_key
    else:
        url = config["url"]
        today = datetime.today()
        yesterday = today - timedelta(days=1)
        params = {
            "account_key": account_key,
            "results": 40,
            "start": yesterday.strftime('%Y-%m-%d %H:%M:%S'),
            "end": today.strftime('%Y-%m-%d %H:%M:%S')
        }
        params_encoded = urlencode(params)
        response = requests.get(f"{url}?{params_encoded}")
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

def runubi_fetch_process():
    results = []
    status_ubibot = "Success"
    try:
        for key in endpoints_config:
            data, endpoint_key = fetch_data_ubi(key)
            if data:
                process_function = endpoints_config[key]["process_function"]
                if "channel_id" in endpoints_config[key]:
                    processed_data = process_function(data, endpoints_config[key]["channel_id"])
                else:
                    processed_data = process_function(data)
                results.append((processed_data, str(endpoint_key)))
    except Exception as e:
        status_ubibot = f'Failed: {e}'
    return results, status_ubibot