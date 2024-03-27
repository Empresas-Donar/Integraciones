import csv
import requests
import os
from datetime import datetime
import json

# Define la API key
API_KEY = "mH2auozP45Z23p1EHwpk"

# ------------------------------------------------------------------------------------------------

# Lista de granjas

def guardar_csv_farm_irrigations(datos, ruta):
    archivo_csv = os.path.join(ruta, 'List_Farm_Irrigation.csv')

    # Verificar si el archivo CSV existe
    datos_nuevos = []
    if os.path.exists(archivo_csv):
        with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
            reader = csv.DictReader(archivo)
            datos_antiguos = list(reader)

        # Verificar si hay datos duplicados y actualizarlos si es necesario
        for dato_nuevo in datos:
            id_nuevo = dato_nuevo['id']
            encontrado = False
            for i, dato_viejo in enumerate(datos_antiguos):
                id_viejo = dato_viejo.get('id')
                if id_viejo == id_nuevo:
                    if dato_viejo != dato_nuevo:
                        datos_antiguos[i] = dato_nuevo
                    encontrado = True
                    break
            if not encontrado:
                datos_nuevos.append(dato_nuevo)
    else:
        datos_nuevos = datos

    # Guardar los datos en el archivo CSV
    with open(archivo_csv, 'w', newline='', encoding='utf-8') as archivo:
        if datos_antiguos:
            fieldnames = datos_antiguos[0].keys()  # Usamos los encabezados existentes si hay datos antiguos
        else:
            fieldnames = datos_nuevos[0].keys()  # Usamos los encabezados de los nuevos datos si no hay datos antiguos
        writer = csv.DictWriter(archivo, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(datos_antiguos + datos_nuevos)

    if datos_nuevos:
        print(f"Datos de irrigaciones reales de farms guardados en '{archivo_csv}'")
    else:
        print("No hay nuevos datos para agregar.")


# -------------------------------------------------------------------------------------------------------------------------------

#Lista de las zonas de cada granja
    
def convertir_id(id_str):
    # Convertir el ID a un formato común, por ejemplo, a entero
    return int(id_str)

def obtener_farm_ids(ruta):
    ids = []
    archivo_csv = os.path.join(ruta, 'List_Farm.csv')
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        for row in reader:
            ids.append(row['id'])
    return ids

def obtener_datos_zonas_farm(farm_id):
    url = f"https://api.wiseconn.com/farms/{farm_id}/zones"
    headers = {
        "api_key": API_KEY,
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def guardar_csv_zonas_farm(datos, ruta):
    archivo_csv = os.path.join(ruta, 'List_Farm_Zone.csv')

    # Verificar si el archivo CSV existe
    datos_nuevos = []
    if os.path.exists(archivo_csv):
        with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
            reader = csv.DictReader(archivo)
            datos_antiguos = list(reader)
        
        # Verificar si hay datos duplicados y actualizarlos si es necesario
        for dato_nuevo in datos:
            id_nuevo = convertir_id(dato_nuevo['id'])
            encontrado = False
            for i, dato_viejo in enumerate(datos_antiguos):
                id_viejo = convertir_id(dato_viejo['id'])
                if id_viejo == id_nuevo:
                    if dato_viejo != dato_nuevo:
                        datos_antiguos[i] = dato_nuevo
                    encontrado = True
                    break
            if not encontrado:
                datos_nuevos.append(dato_nuevo)
    else:
        datos_nuevos = datos
    
    # Guardar los datos en el archivo CSV
    if datos_nuevos:
        with open(archivo_csv, 'w', newline='', encoding='utf-8') as archivo:
            writer = csv.DictWriter(archivo, fieldnames=datos[0].keys())
            writer.writeheader()
            writer.writerows(datos_antiguos + datos_nuevos)
        print(f"Datos de zonas de farms guardados en '{archivo_csv}'")
    else:
        print("No hay nuevos datos para agregar.")

def main():
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API\Prueba 2"
    ids_granjas = obtener_farm_ids(ruta)
    for farm_id in ids_granjas:
        datos_zonas_farm = obtener_datos_zonas_farm(farm_id)
        guardar_csv_zonas_farm(datos_zonas_farm, ruta)

if __name__ == "__main__":
    main()

#------------------------------------------------------------------------------------------------------------
    
#Lsita de sistemas de bombas de cada granja
    
def convertir_id(id_str):
    # Convertir el ID a un formato común, por ejemplo, a entero
    return int(id_str)

def obtener_farm_ids(ruta):
    ids = []
    archivo_csv = os.path.join(ruta, 'List_Farm.csv')
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        for row in reader:
            ids.append(row['id'])
    return ids

def obtener_datos_pump_systems(farm_id):
    url = f"https://api.wiseconn.com/farms/{farm_id}/pumpSystems"
    headers = {
        "api_key": API_KEY,
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def guardar_csv_pump_systems(datos, ruta):
    archivo_csv = os.path.join(ruta, 'List_System_Pumps_Farm.csv')

    # Verificar si el archivo CSV existe
    datos_nuevos = []
    if os.path.exists(archivo_csv):
        with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
            reader = csv.DictReader(archivo)
            datos_antiguos = list(reader)
        
        # Verificar si hay datos duplicados y actualizarlos si es necesario
        for dato_nuevo in datos:
            id_nuevo = convertir_id(dato_nuevo['id'])
            encontrado = False
            for i, dato_viejo in enumerate(datos_antiguos):
                id_viejo = convertir_id(dato_viejo['id'])
                if id_viejo == id_nuevo:
                    if dato_viejo != dato_nuevo:
                        datos_antiguos[i] = dato_nuevo
                    encontrado = True
                    break
            if not encontrado:
                datos_nuevos.append(dato_nuevo)
    else:
        datos_nuevos = datos
    
    # Guardar los datos en el archivo CSV
    if datos_nuevos:
        with open(archivo_csv, 'w', newline='', encoding='utf-8') as archivo:
            writer = csv.DictWriter(archivo, fieldnames=datos[0].keys())
            writer.writeheader()
            writer.writerows(datos_antiguos + datos_nuevos)
        print(f"Datos de sistemas de bombas de farms guardados en '{archivo_csv}'")
    else:
        print("No hay nuevos datos para agregar.")

def main():
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API\Prueba 2"
    ids_granjas = obtener_farm_ids(ruta)
    for farm_id in ids_granjas:
        datos_pump_systems = obtener_datos_pump_systems(farm_id)
        guardar_csv_pump_systems(datos_pump_systems, ruta)

if __name__ == "__main__":
    main()

#-------------------------------------------------------------------------------------------------------------------------------------
    
#Lista de riego por zona
    
def obtener_zone_ids(ruta):
    ids = []
    archivo_csv = os.path.join(ruta, 'List_Farm_Zone.csv')
    with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
        reader = csv.DictReader(archivo)
        for row in reader:
            ids.append(row['id'])
    return ids

def obtener_fecha_actual():
    ahora = datetime.now()
    fecha_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fecha_fin = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)
    return fecha_inicio, fecha_fin

def obtener_datos_real_irrigations(zone_id):
    url = f"https://api.wiseconn.com/zones/{zone_id}/realIrrigations"
    # Obtener la fecha actual
    fecha_inicio, fecha_fin = obtener_fecha_actual()
    # Convertir las fechas en el formato esperado por la API
    init_time = fecha_inicio.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time = fecha_fin.strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {
        "api_key": API_KEY,
        "Accept": "application/json"
    }
    params = {
        "endTime": end_time,
        "initTime": init_time
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def guardar_csv_real_irrigations(datos, ruta):
    archivo_csv = os.path.join(ruta, 'List_Zone_Irrigation.csv')

    # Verificar si el archivo CSV existe
    datos_nuevos = []
    if os.path.exists(archivo_csv):
        with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
            reader = csv.DictReader(archivo)
            datos_antiguos = list(reader)
        
        # Verificar si hay datos duplicados y actualizarlos si es necesario
        for dato_nuevo in datos:
            id_nuevo = dato_nuevo['id']
            encontrado = False
            for i, dato_viejo in enumerate(datos_antiguos):
                if dato_viejo['id'] == id_nuevo:
                    if dato_viejo != dato_nuevo:
                        datos_antiguos[i] = dato_nuevo
                    encontrado = True
                    break
            if not encontrado:
                datos_nuevos.append(dato_nuevo)
    else:
        datos_nuevos = datos
    
    # Guardar los datos en el archivo CSV
    if datos_nuevos:
        with open(archivo_csv, 'w', newline='', encoding='utf-8') as archivo:
            writer = csv.DictWriter(archivo, fieldnames=datos[0].keys())
            writer.writeheader()
            writer.writerows(datos_antiguos + datos_nuevos)
        print(f"Datos de irrigaciones reales de zonas guardados en '{archivo_csv}'")
    else:
        print("No hay nuevos datos para agregar.")

def main():
    ruta = r"C:\Users\gesti\OneDrive\Oficina Administraciones Donar\02 - Control de Gestión\15 - Desarrollos\Programa lector API\Prueba 2"
    ids_zonas = obtener_zone_ids(ruta)
    for zone_id in ids_zonas:
        datos_real_irrigations = obtener_datos_real_irrigations(zone_id)
        guardar_csv_real_irrigations(datos_real_irrigations, ruta)

if __name__ == "__main__":
    main()

#------------------------------------------------------------------------------------------------------------------------------------

# Lista de riego por granja    

