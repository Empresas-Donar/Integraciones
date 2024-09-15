import logging
import time
import psutil  # Para medir uso de recursos
from concurrent.futures import ThreadPoolExecutor, as_completed
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
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])  

app = create_app()

def process_data(fetch_process_func, manage_data_func, source_name):
    with app.app_context():
        try:
            data_content, status = fetch_process_func()
            logging.info(f"Status {source_name}: {status}")
            if status.startswith("Success"):
                for data, data_type in data_content:
                    manage_data_func(data, data_type)
                    logging.info(f"Datos procesados para {data_type} de {source_name}")
            return status
        except Exception as e:
            logging.error(f"Error en {source_name}: {e}")
            return f"Error: {e}"
        finally:
            db.session.remove()

def main():

    start_time = time.time() 
    process = psutil.Process()  
    start_memory_usage = process.memory_info().rss / (1024 ** 2)  


    with ThreadPoolExecutor(max_workers=80) as executor:
        futures = {
            executor.submit(process_data, run_fetch_process, manage_data, "Wiseconn"): "Wiseconn",
            executor.submit(process_data, runubi_fetch_process, manage_data_ubi, "Ubibot"): "Ubibot"
        }


        status_results = {}
        for future in as_completed(futures):
            source_name = futures[future]
            try:
                status = future.result()
                status_results[f"status_{source_name.lower()}"] = status
                logging.info(f"Proceso completado para {source_name}: {status}")
            except Exception as exc:
                logging.error(f"Error en {source_name}: {exc}")
                status_results[f"status_{source_name.lower()}"] = f"Error: {exc}"


    status_wiseconn = status_results.get("status_wiseconn")
    status_ubibot = status_results.get("status_ubibot")
    
    if status_ubibot.startswith("Success"):
        with app.app_context():
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
    

    end_time = time.time()  
    total_time = end_time - start_time  
    
    cpu_usage = psutil.cpu_percent(interval=1)  
    end_memory_usage = process.memory_info().rss / (1024 ** 2)  

    memory_usage = end_memory_usage - start_memory_usage

    logging.info(f"Tiempo total de ejecución: {total_time:.2f} segundos")
    logging.info(f"Uso promedio de CPU: {cpu_usage:.2f}%")
    logging.info(f"Memoria usada: {memory_usage:.2f} MB")

    print(f"Tiempo total de ejecución: {total_time:.2f} segundos")
    print(f"Uso promedio de CPU: {cpu_usage:.2f}%")
    print(f"Memoria usada: {memory_usage:.2f} MB")
    
    return {"status_wiseconn": status_wiseconn, "status_ubibot": status_ubibot}

if __name__ == "__main__":
    status = main()
    print(json.dumps(status), flush=True)
