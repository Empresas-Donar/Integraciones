# Import necessary libraries and run the application that starts the chain.
from app import create_app
from app.services.wiseconn import run_fetch_process
from app.services.ubibot import runubi_fetch_process
from app.services.database import manage_data
from app.services.database_ubibot import manage_data_ubi

app = create_app()
def process_data(fetch_process_func, manage_data_func, source_name):
    data_content, status = fetch_process_func()
    print(f"Status {source_name}: {status}")
    if status.startswith("Success"):
        for data, data_type in data_content:
            manage_data_func(data, data_type)
            print(f"Datos procesados para {data_type} de {source_name}")

def main():
    with app.app_context():
        process_data(run_fetch_process, manage_data, "Wiseconn")
        process_data(runubi_fetch_process, manage_data_ubi, "Ubibot")

if __name__ == "__main__":
    main()