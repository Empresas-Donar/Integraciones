# Incorporates extra useful functions

import pandas as pd
import uuid

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
                print(f"Columnas faltantes para channel_id: {channel_id}, field: {field}")
    final_df = pd.DataFrame(rows)
    print(f"Total de filas en final_df: {len(final_df)}")
    return final_df
