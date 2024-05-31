# Import necessary libraries and run the application that starts the chain.

from app import create_app
from app.services.wiseconn import run_fetch_process
from app.services.database import manage_data

app = create_app()

def main():
    with app.app_context():
        print("Inicio del proceso de datos...", flush=True)
        processed_data_list = run_fetch_process()
        for data, data_type in processed_data_list:
            if data is not None:
                manage_data(data, data_type)
                print(f"Datos procesados para {data_type}", flush=True)

if __name__ == "__main__":
    main()
