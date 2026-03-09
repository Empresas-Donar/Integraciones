"""
Backfill de wc_zones_sensors desde una fecha de inicio hasta hoy.
Procesa por chunks de N días para no sobrecargar la API.

Uso:
    python backfill_sensors.py                          # desde 2024-10-19 hasta hoy
    python backfill_sensors.py --start 2025-01-01      # desde fecha específica
    python backfill_sensors.py --chunk-days 14          # chunks de 14 días
    python backfill_sensors.py --dry-run               # sin insertar en DB
"""

import argparse
import datetime
import logging
import os
import sys
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# Silenciar logs internos del proyecto
logging.getLogger('data_processing').setLevel(logging.WARNING)

from app import create_app, db
from app.models import WCZonesSensors
from app.services.wiseconn import fetch_data, endpoints_config, generate_farm_endpoints
from app.services.data_processing import process_data_measures, process_sensor_data
from sqlalchemy import text
import pandas as pd

API_KEY = os.getenv('API_KEY')


def fetch_sensor_range(sensor_id, init_time, end_time):
    """Llama a la API de Wiseconn con un rango de fechas específico."""
    url = f"https://api.wiseconn.com/measures/{sensor_id}/data"
    headers = {"api_key": API_KEY}
    params = {
        "initTime": init_time.strftime("%Y-%m-%d"),
        "endTime": end_time.strftime("%Y-%m-%d"),
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning(f"  Error sensor {sensor_id} [{init_time} - {end_time}]: {e}")
        return None


def get_existing_keys(chunk_start, chunk_end):
    """Carga claves existentes en el rango de fechas del chunk."""
    result = db.session.execute(text("""
        SELECT created_at, sensor_id, farm_id, zone_id
        FROM wc_zones_sensors
        WHERE created_at >= :start AND created_at < :end
    """), {"start": chunk_start, "end": chunk_end}).fetchall()

    return set(
        (str(row[0]), str(row[1]), str(row[2]), str(row[3]) if row[3] else None)
        for row in result
    )


def insert_records(records, dry_run=False):
    if not records:
        return 0
    if dry_run:
        log.info(f"    [DRY-RUN] Se insertarían {len(records)} registros")
        return len(records)
    try:
        db.session.bulk_save_objects(records)
        db.session.commit()
        return len(records)
    except Exception as e:
        db.session.rollback()
        log.error(f"    Error insertando: {e}")
        return 0


def backfill(start_date, end_date, chunk_days=30, dry_run=False, delay=0.2):
    app = create_app()

    with app.app_context():
        log.info("Obteniendo farms y sensores...")
        farms_data = fetch_data("farms")
        if not farms_data:
            log.error("No se pudo obtener farms. Abortando.")
            sys.exit(1)

        generate_farm_endpoints(farms_data)

        # Construir mapa sensor_id -> (measure_info, farmId)
        sensor_map = {}
        for farm in farms_data:
            farmid = str(farm['id'])
            measures_data = fetch_data(f"measures_{farm['id']}")
            if not measures_data:
                continue
            processed = process_data_measures(measures_data)
            for item in processed['processed_items']:
                sensor_map[item['sensor_id']] = (item, farmid)

        total_sensors = len(sensor_map)
        log.info(f"Total sensores: {total_sensors}")

        # Generar chunks de fechas
        chunks = []
        current = start_date
        while current < end_date:
            chunk_end = min(current + datetime.timedelta(days=chunk_days), end_date)
            chunks.append((current, chunk_end))
            current = chunk_end

        log.info(f"Rango: {start_date} -> {end_date} | {len(chunks)} chunks de {chunk_days} días")
        log.info("=" * 60)

        total_inserted = 0
        total_skipped = 0

        for chunk_idx, (chunk_start, chunk_end) in enumerate(chunks, 1):
            log.info(f"\nChunk {chunk_idx}/{len(chunks)}: {chunk_start} -> {chunk_end}")

            existing_keys = get_existing_keys(chunk_start, chunk_end)
            log.info(f"  Registros existentes en chunk: {len(existing_keys)}")

            records_to_add = []
            sensors_processed = 0

            for sensor_id, (measure_info, farmid) in sensor_map.items():
                raw_data = fetch_sensor_range(sensor_id, chunk_start, chunk_end)
                time.sleep(delay)

                if not raw_data:
                    continue

                processed_sd = process_sensor_data(raw_data, farmid)

                zone_id = measure_info.get('zone_id')
                if pd.isna(zone_id) if zone_id is not None else False:
                    zone_id = None
                else:
                    zone_id = str(zone_id) if zone_id is not None else None

                for v in processed_sd['values']:
                    created_at = v.get('created_at')
                    key = (str(created_at), str(sensor_id), str(farmid), zone_id)
                    if key in existing_keys:
                        total_skipped += 1
                        continue

                    records_to_add.append(WCZonesSensors(
                        sensor_id=sensor_id,
                        name=measure_info.get('name'),
                        unit=measure_info.get('unit'),
                        values=v.get('value'),
                        created_at=created_at,
                        date=v.get('date'),
                        hour=v.get('hour'),
                        zone_id=zone_id,
                        farm_id=farmid,
                    ))
                    existing_keys.add(key)

                sensors_processed += 1
                if sensors_processed % 20 == 0:
                    log.info(f"  Sensores procesados: {sensors_processed}/{total_sensors} | Pendientes insertar: {len(records_to_add)}")

            inserted = insert_records(records_to_add, dry_run=dry_run)
            total_inserted += inserted
            log.info(f"  Chunk {chunk_idx} completado: {inserted} insertados, {total_skipped} omitidos (ya existían)")

        log.info("\n" + "=" * 60)
        log.info(f"BACKFILL COMPLETADO")
        log.info(f"  Total insertados: {total_inserted}")
        log.info(f"  Total omitidos:   {total_skipped}")
        log.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill wc_zones_sensors")
    parser.add_argument("--start", default="2024-10-19", help="Fecha inicio YYYY-MM-DD (default: 2024-10-19)")
    parser.add_argument("--end", default=None, help="Fecha fin YYYY-MM-DD (default: hoy)")
    parser.add_argument("--chunk-days", type=int, default=30, help="Días por chunk (default: 30)")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay entre llamadas API en segundos (default: 0.2)")
    parser.add_argument("--dry-run", action="store_true", help="Sin insertar en DB, solo mostrar qué se insertaría")
    args = parser.parse_args()

    start_date = datetime.date.fromisoformat(args.start)
    end_date = datetime.date.fromisoformat(args.end) if args.end else datetime.date.today()

    if start_date >= end_date:
        log.error("--start debe ser anterior a --end")
        sys.exit(1)

    log.info(f"Iniciando backfill: {start_date} -> {end_date} | chunk={args.chunk_days}d | dry_run={args.dry_run}")
    backfill(start_date, end_date, chunk_days=args.chunk_days, dry_run=args.dry_run, delay=args.delay)
