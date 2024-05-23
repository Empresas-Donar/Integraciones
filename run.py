from app import create_app
from app.services.wiseconn import run_fetch_process
from app.services.database import manage_data

app = create_app()

def main():
    with app.app_context():  # Crear un contexto de aplicación
        processed_data_list = run_fetch_process()  # Esta función debería devolver una lista de tuplas (data, data_type)
        for data, data_type in processed_data_list:  # Desempaquetar la tupla correctamente
            if data is not None:
                manage_data(data, data_type)  # Pasar ambos data y data_type a manage_data

if __name__ == "__main__":
    main()

