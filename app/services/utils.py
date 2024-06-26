# Incorporates extra useful functions

import pandas as pd

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