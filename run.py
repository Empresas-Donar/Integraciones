# run.py

import logging
from app import create_app, db
from app.services.wiseconn import run_fetch_process
from app.services.ubibot import runubi_fetch_process
from app.services.database import manage_data
from app.services.database_ubibot import manage_data_ubi, manage_fields_ubi
from app.services.utils import create_channel_sensor_mapping, create_final_dataframe
from app.models import ExecutionLog
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = create_app()

def process_data(fetch_process_func, manage_data_func, source_name):
    data_content, status = fetch_process_func()
    logging.info(f"Status {source_name}: {status}")
    if status.startswith("Success"):
        for data, data_type in data_content:
            manage_data_func(data, data_type)
            logging.info(f"Datos procesados para {data_type} de {source_name}")
    return status

def main():
    with app.app_context():
        status_wiseconn = process_data(run_fetch_process, manage_data, "Wiseconn")
        status_ubibot = process_data(runubi_fetch_process, manage_data_ubi, "Ubibot")
        
        from app.services.data_processing import raw_data_ubi_channels, raw_df_summary
        raw_df_summary['channel_id'] = raw_df_summary['channel_id'].astype(int)
        channel_mapping = create_channel_sensor_mapping(raw_data_ubi_channels)
        final_df = create_final_dataframe(channel_mapping, raw_df_summary)
        manage_fields_ubi(final_df)
        
        log = ExecutionLog(
            status_wiseconn=status_wiseconn,
            status_ubibot=status_ubibot,
            date=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        logging.info(f"Registro añadido con estados - Wiseconn: {status_wiseconn}, Ubibot: {status_ubibot}")
    
    return {"status_wiseconn": status_wiseconn, "status_ubibot": status_ubibot}

if __name__ == "__main__":
    status = main()
    print(json.dumps(status), flush=True)

