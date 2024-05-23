import requests
from .data_processing import process_data_wc_farms_zones, process_data_irrigation

# Configuración de endpoints con sus correspondientes funciones de procesamiento.
# Cada endpoint tiene una URL específica, parámetros opcionales y una función para procesar los datos recibidos.
endpoints_config = {
    "zones": {
        "url": "https://api.wiseconn.com/farms/14245/zones",
        "process_function": process_data_wc_farms_zones
    },
    "irrigations": {
        "url": "https://api.wiseconn.com/farms/14245/irrigations",
        "params": {"initTime": "2024-02-02", "endTime": "2024-02-03"},
        "process_function": process_data_irrigation
    }
}

api_key = "mH2auozP45Z23p1EHwpk"  # Clave API para la autenticación en la API de Wiseconn.

def fetch_data(endpoint_key):
    # Obtener la configuración del endpoint usando la clave proporcionada.
    config = endpoints_config[endpoint_key]
    headers = {"api_key": api_key}  # Encabezados necesarios para la solicitud, incluyendo la API key.

    # Realizar la solicitud GET al endpoint especificado.
    response = requests.get(config["url"], headers=headers, params=config.get("params", {}))
    try:
        response.raise_for_status()  # Verificar si la respuesta es exitosa (código 200).
        return response.json()  # Devolver los datos JSON de la respuesta.
    except requests.HTTPError as e:
        # Manejo de errores en caso de respuesta no exitosa.
        print(f"Error fetching data from {config['url']}: {e}")
        return None  # Devolver None si ocurre un error.

def process_all_endpoints():
    results = []
    for key in endpoints_config:
        data = fetch_data(key)  # Obtener datos para cada endpoint configurado.
        if data:  # Verificar si se recibieron datos correctamente.
            # Procesar los datos utilizando la función asignada en la configuración del endpoint.
            processed_data = endpoints_config[key]["process_function"](data)
            results.append(processed_data)  # Añadir los datos procesados a la lista de resultados.
    return results  # Devolver la lista de todos los datos procesados.

def run_fetch_process():
    results = []
    for key in endpoints_config:
        data = fetch_data(key)
        if data:  # Verificar si se recibieron datos correctamente.
            processed_data = endpoints_config[key]["process_function"](data)
            results.append((processed_data, key))  # Añadir una tupla de (datos procesados, tipo de datos)
    return results

