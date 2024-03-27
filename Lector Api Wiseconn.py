# Obtener el listado de las granjas

import os
import requests
import csv

API_KEY = "mH2auozP45Z23p1EHwpk"

def obtener_datos(api_key): # Realiza una solicitud GET a la URL de la API proporcionada, pasando la API key en los encabezados. Devuelve los datos de la respuesta en formato JSON 
    url = "https://api.wiseconn.com/farms"
    headers = {
        "accept": "application/json",
        "api_key": api_key
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Lanza una excepción para errores HTTP
        datos = response.json()
        return datos
    except requests.exceptions.RequestException as e:
        print("Error al hacer la solicitud:", e)
        return None

def guardar_csv(datos, ruta): # ecibe los datos obtenidos de la API y la ruta donde se debe guardar el archivo CSV. Utiliza la biblioteca csv para escribir los datos en un archivo CSV llamado "List_Farm.csv" en la ruta especificada.
    if datos:
        ruta_completa = os.path.join(ruta, 'List_Farm.csv')
        with open(ruta_completa, 'w', newline='', encoding='utf-8') as archivo_csv:
            writer = csv.DictWriter(archivo_csv, fieldnames=datos[0].keys())
            writer.writeheader()
            writer.writerows(datos)
        print(f"Datos de las granjas guardados en '{ruta_completa}'")
    else:
        print("No se pudieron obtener los datos.")

def main(): # es la función principal que ejecuta el programa. Llama a obtener_datos() para obtener los datos de las granjas, y luego llama a guardar_csv() para guardar esos datos en un archivo CSV.
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API"
    datos = obtener_datos(API_KEY)
    guardar_csv(datos, ruta)

if __name__ == "__main__": # Se verifica que el programa se esté ejecutando como el script principal antes de llamar a main() para asegurarse de que el código se ejecute solo cuando se llame al archivo directamente, no cuando se importe como un módulo.
    main()

# ----------------------------------------------------------------------------------

# Obtener la planificación del riego por granja 

import os
import csv
import requests
from datetime import datetime


def obtener_ids(ruta):
    ids = []
    archivo_csv = os.path.join(ruta, 'List_Farm.csv')
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        for row in reader:
            ids.append(row['id'])
    return ids

def obtener_fecha_actual():
    ahora = datetime.now()
    fecha_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_fin = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)
    return fecha_inicio, fecha_fin  # Devolver objetos datetime

def obtener_datos_irrigation(api_key, farm_id, init_time, end_time):
    url = f"https://api.wiseconn.com/farms/{farm_id}/irrigations"
    headers = {
        "accept": "application/json",
        "api_key": api_key
    }
    init_time_str, end_time_str = init_time.strftime('%Y-%m-%dT%H:%M:%SZ'), end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    params = {
        "initTime": init_time_str,
        "endTime": end_time_str
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        datos = response.json()
        return datos
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos de irrigación de la granja {farm_id}: {e}")
        return None
    
def _existe_datos(archivo_csv, datos):
    # Cargar todos los datos del archivo CSV en una lista
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        filas = list(reader)

    # Comparar los nuevos datos con las filas existentes
    for dato in datos:
        if dato in filas:
            return True
    return False

def guardar_csv_irrigation(datos, ruta):
    if datos:
        archivo_csv = os.path.join(ruta, 'Programacion_Riego.csv')
        modo = 'a' if os.path.exists(archivo_csv) else 'w'
        
        # Verificar si los datos ya existen en el archivo CSV
        if modo == 'a' and _existe_datos(archivo_csv, datos):
            print("Los datos ya existen en el archivo. No se agregaron datos duplicados.")
            return
        
        with open(archivo_csv, modo, newline='', encoding='utf-8') as archivo:
            writer = csv.DictWriter(archivo, fieldnames=datos[0].keys())
            if modo == 'w':
                writer.writeheader()
            
            # Escribir solo los valores numéricos en el archivo CSV
            for dato in datos:
                dato['volume'] = dato['volume']['value']
                dato['precipitation'] = dato['precipitation']['value']
                dato['theoricalFlow'] = dato['theoricalFlow']['value']
                writer.writerow(dato)
                
        print(f"Datos de irrigación guardados en '{archivo_csv}'")
    else:
        print("No se pudieron obtener los datos de irrigación.")


def main():
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API"
    ids = obtener_ids(ruta)
    fecha_inicio, fecha_fin = obtener_fecha_actual()
    for id_granja in ids:
        datos_irrigation = obtener_datos_irrigation(API_KEY, id_granja, fecha_inicio, fecha_fin)
        guardar_csv_irrigation(datos_irrigation, ruta)

if __name__ == "__main__":
    main()

"--------------------------------------------------------------------------------------------------------------"   


# Obtener el listado de las zonas de riego por granja

import os
import csv
import requests

# Función para obtener los IDs de las granjas desde el archivo CSV
def obtener_ids(ruta):
    ids = []
    archivo_csv = os.path.join(ruta, 'List_Farm.csv')
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        for row in reader:
            ids.append(row['id'])
    return ids

# Función para obtener las zonas de una granja específica

def obtener_zonas_irrigacion(api_key, farm_id):
    url = f"https://api.wiseconn.com/farms/{farm_id}/zones"
    headers = {
        "accept": "application/json",
        "api_key": api_key
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener zonas de irrigación para la granja {farm_id}: {e}")
        return None

# Función para guardar los datos en un archivo CSV
def guardar_csv(datos, ruta):
    archivo_csv = os.path.join(ruta, 'List_Farm_Zone.csv')
    with open(archivo_csv, 'w', newline='', encoding='utf-8') as archivo:
        writer = csv.DictWriter(archivo, fieldnames=datos[0].keys())
        writer.writeheader()
        writer.writerows(datos)
    print(f"Datos de zonas de irrigación guardados en '{archivo_csv}'")

# Función principal
def main():
    # Ruta donde se encuentra el archivo CSV y donde se guardará el nuevo archivo
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API"
    # API key de Wiseconn
    api_key = "mH2auozP45Z23p1EHwpk"
    # Obtener los IDs de las granjas
    ids_granjas = obtener_ids(ruta)
    # Lista para almacenar los datos de zonas de irrigación
    datos_zonas_irrigacion = []
    # Iterar sobre cada ID de granja y obtener las zonas de irrigación
    for id_granja in ids_granjas:
        zonas_irrigacion = obtener_zonas_irrigacion(api_key, id_granja)
        if zonas_irrigacion:
            # Agregar los datos de las zonas de irrigación a la lista
            datos_zonas_irrigacion.extend(zonas_irrigacion)
    # Guardar los datos en un archivo CSV
    guardar_csv(datos_zonas_irrigacion, ruta)

if __name__ == "__main__":
    main()


"----------------------------------------------------"

# Lsita riego por granja

import os
import csv
import requests
from datetime import datetime

# Agregar la función obtener_fecha_actual
def obtener_fecha_actual():
    ahora = datetime.now()
    fecha_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_fin = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)
    return fecha_inicio, fecha_fin

# Función para leer el archivo List_Farm.csv y obtener los IDs de las granjas
def obtener_ids_granjas(ruta):
    ids = []
    archivo_csv = os.path.join(ruta, 'List_Farm.csv')
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        for row in reader:
            ids.append(row['id'])
    return ids

# Función para obtener los datos de irrigación de una granja específica en un rango de fechas
def obtener_datos_irrigacion(api_key, farm_id, init_time, end_time):
    url = f"https://api.wiseconn.com/farms/{farm_id}/realIrrigations"
    headers = {
        "accept": "application/json",
        "api_key": api_key
    }
    params = {
        "initTime": init_time,
        "endTime": end_time
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        datos = response.json()
        return datos
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos de irrigación para la granja {farm_id}: {e}")
        return None

# Función para guardar los datos en un archivo CSV
def guardar_csv(datos, ruta):
    if datos:
        archivo_csv = os.path.join(ruta, 'List_Farm_Irrigation.csv')
        modo = 'a' if os.path.exists(archivo_csv) else 'w'
        
        # Verificar si los datos ya existen en el archivo CSV
        if modo == 'a':
            datos_antiguos = leer_csv(archivo_csv)
            nuevos_datos = []
            for dato in datos:
                # Verificar si el ID ya existe en el archivo CSV
                if any(d['id'] == dato['id'] for d in datos_antiguos):
                    # Reemplazar los datos existentes con los nuevos
                    datos_antiguos = [d if d['id'] != dato['id'] else dato for d in datos_antiguos]
                else:
                    # Agregar los nuevos datos
                    nuevos_datos.append(dato)
            
            if not nuevos_datos:
                print("No hay nuevos datos para agregar.")
                return
            else:
                datos = datos_antiguos + nuevos_datos
        
        with open(archivo_csv, modo, newline='', encoding='utf-8') as archivo:
            writer = csv.DictWriter(archivo, fieldnames=datos[0].keys())
            if modo == 'w':
                writer.writeheader()
            writer.writerows(datos)
                
        print(f"Datos de irrigación de las granjas guardados en '{archivo_csv}'")
    else:
        print("No se pudieron obtener datos de irrigación de las granjas.")

# Función para leer los datos de un archivo CSV
def leer_csv(archivo_csv):
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        datos = [fila for fila in reader]
    return datos

# Función principal
def main():
    # Ruta donde se encuentra el archivo CSV y donde se guardará el nuevo archivo
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API"
    # API key de Wiseconn
    api_key = "mH2auozP45Z23p1EHwpk"
    # Obtener las fechas actuales
    fecha_inicio, fecha_fin = obtener_fecha_actual()
    # Obtener los IDs de las granjas desde el archivo CSV
    ids_granjas = obtener_ids_granjas(ruta)
    # Lista para almacenar los datos de irrigación de todas las granjas
    datos_granjas_irrigacion = []
    # Iterar sobre cada ID de granja y obtener los datos de irrigación
    for id_granja in ids_granjas:
        datos_irrigacion = obtener_datos_irrigacion(api_key, id_granja, fecha_inicio, fecha_fin)
        if datos_irrigacion:
            # Agregar los datos de irrigación de la granja a la lista
            datos_granjas_irrigacion.extend(datos_irrigacion)
    # Guardar los datos en un archivo CSV
    guardar_csv(datos_granjas_irrigacion, ruta)

if __name__ == "__main__":
    main()


"-------------------------------------------------------------------------------------------------"

# Datos Reales de Irrigación

import os
import csv
import requests

def obtener_valor_numerico(dato):
    return dato['value'] if isinstance(dato, dict) and 'value' in dato else None

def obtener_datos_irrigation(api_key, irrigation_id):
    url = f"https://api.wiseconn.com/realIrrigations/{irrigation_id}"
    headers = {
        "accept": "application/json",
        "api_key": api_key
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        datos = response.json()
        return datos
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos de irrigación para el ID {irrigation_id}: {e}")
        return None

def leer_archivo_list_farm_irrigation(ruta):
    datos_irrigation = []
    archivo_csv = os.path.join(ruta, 'Get_Real_Irrigation.csv')
    if os.path.exists(archivo_csv):
        with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
            reader = csv.DictReader(archivo)
            for row in reader:
                datos_irrigation.append(row)
    return datos_irrigation

def guardar_csv(data, ruta):
    archivo_csv = os.path.join(ruta, 'Get_Real_Irrigation.csv')
    modo = 'a' if os.path.exists(archivo_csv) else 'w'
    with open(archivo_csv, modo, newline='', encoding='utf-8') as archivo:
        writer = csv.DictWriter(archivo, fieldnames=data[0].keys())
        if modo == 'w':
            writer.writeheader()
        writer.writerows(data)

def main():
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API"
    datos_irrigation = leer_archivo_list_farm_irrigation(ruta)
    ids_existentes = set([dato['id'] for dato in datos_irrigation])

    nuevos_datos_irrigation_real = []
    for dato in datos_irrigation:
        irrigation_id = dato['id']
        datos = obtener_datos_irrigation(API_KEY, irrigation_id)
        if datos:
            nuevo_dato = {
                'id': irrigation_id,
                'volume': obtener_valor_numerico(datos.get('volume', {})),
                'precipitation': obtener_valor_numerico(datos.get('precipitation', {})),
                'flow': obtener_valor_numerico(datos.get('flow', {})),
                'instantaneousFlow': obtener_valor_numerico(datos.get('instantaneousFlow', {}))
            }
            if irrigation_id not in ids_existentes:
                nuevos_datos_irrigation_real.append(nuevo_dato)
                ids_existentes.add(irrigation_id)

    if nuevos_datos_irrigation_real:
        guardar_csv(nuevos_datos_irrigation_real, ruta)
        print(f"Datos de irrigación reales nuevos guardados en '{ruta}'")
    else:
        print("No se encontraron nuevos datos de irrigación reales.")

if __name__ == "__main__":
    main()

"---------------------------------------------------------------------------------------"

# Lista de sistemas de bombas

import os
import csv
import requests

def obtener_datos_pump_system(api_key, farm_id):
    url = f"https://api.wiseconn.com/farms/{farm_id}/pumpSystems"
    headers = {
        "accept": "application/json",
        "api_key": api_key
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        datos = response.json()
        return datos
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos de sistemas de bombas para la granja {farm_id}: {e}")
        return None

def leer_archivo_list_farm(ruta):
    datos_farm = []
    archivo_csv = os.path.join(ruta, 'List_Farm.csv')
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        for row in reader:
            datos_farm.append(row)
    return datos_farm

def guardar_csv(data, ruta):
    archivo_csv = os.path.join(ruta, 'List_Pump_System.csv')
    with open(archivo_csv, 'w', newline='', encoding='utf-8') as archivo:
        writer = csv.DictWriter(archivo, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def main():
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API"
    datos_farm = leer_archivo_list_farm(ruta)
    datos_pump_system = []
    for farm in datos_farm:
        farm_id = farm['id']
        datos = obtener_datos_pump_system(API_KEY, farm_id)
        if datos:
            for pump_system in datos:
                pump_system['farmId'] = farm_id
                datos_pump_system.append(pump_system)
        else:
            print(f"No se pudieron obtener datos de sistemas de bombas para la granja {farm_id}")

    if datos_pump_system:
        guardar_csv(datos_pump_system, ruta)
        print(f"Datos de sistemas de bombas guardados en '{ruta}'")
    else:
        print("No se pudieron obtener datos de sistemas de bombas.")

if __name__ == "__main__":
    main()

    "---------------------------------------------------------------------------------------------------------------------------"

    #