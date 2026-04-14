"""
Backfill wc_ema with correct daily aggregates from the Wiseconn API.

The pipeline stores only the last value per day (midnight snapshot), which is
always 0 for daytime sensors like solar radiation and wind speed. This script
fetches the full 15-minute time series per sensor and computes the correct
daily aggregate (MAX for instantaneous sensors, SUM for cumulative ones).

Aggregation strategy:
  - Temperatura         → AVG  (mean temperature for the day)
  - Humedad Relativa    → AVG
  - Presión Atmosférica → AVG
  - Radiacion Solar     → MAX  (peak radiation)
  - Pluviometría        → MAX  (daily accumulated total, already cumulative)
  - Velocidad Viento    → AVG  (mean wind speed)
  - Rafaga Viento       → MAX  (peak gust)
  - Dirección Viento    → AVG  (mean direction — simplification, valid for unimodal wind)
"""

import os
import sys
import time
import requests
import psycopg2
import psycopg2.extras
from datetime import date, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.local'))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

API_KEY = os.getenv('API_KEY')
HEADERS = {'api_key': API_KEY}
DB_CONNECT_KWARGS = dict(
    host="34.176.199.22",
    port=5432,
    dbname="donar_prod",
    user="donar",
    password="N7@pX9!K2L#fQ8rM$D5WcE%ZJ^H@A3",
)
BASE_URL  = 'https://api.wiseconn.com'

# EMA sensors for farm 14245 (Zuñiga) with their aggregation method
EMA_SENSORS = {
    '1-214559': ('radiacion_solar_wm2',    'MAX'),
    '1-214560': ('humedad_relativa_pct',   'AVG'),
    '1-214561': ('pluviometria_mm',        'MAX'),
    '1-214562': ('velocidad_viento_kmh',   'AVG'),
    '1-214563': ('temperatura_c',          'AVG'),
    '1-214564': ('direccion_viento_deg',   'AVG'),
    '1-214565': ('rafaga_viento_kmh',      'MAX'),
    '1-214566': ('presion_atmosferica_pa', 'AVG'),
}

FARM_ID = '14245'
FIELD   = 'ZUÑIGA'

# Fetch in monthly chunks to avoid API timeouts
CHUNK_DAYS = 30


def fetch_sensor_month(sensor_id, start: date, end: date):
    params = {
        'initTime': start.strftime('%Y-%m-%d'),
        'endTime':  end.strftime('%Y-%m-%d'),
    }
    for attempt in range(3):
        try:
            r = requests.get(
                f'{BASE_URL}/measures/{sensor_id}/data',
                headers=HEADERS, params=params, timeout=30
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f'  [retry {attempt+1}] {sensor_id} {start}–{end}: {e}')
            time.sleep(5)
    return []


def aggregate_daily(records, method):
    """Group 15-min records by UTC date, apply aggregation, return {date: value}."""
    from datetime import datetime, timezone
    daily = defaultdict(list)
    for rec in records:
        t = datetime.fromisoformat(rec['time'].replace('Z', '+00:00'))
        # Convert UTC → Santiago (UTC-3 / UTC-4) — use date at local midnight
        local_t = t.astimezone(tz=None)
        d = local_t.date()
        v = rec.get('value')
        if v is not None:
            daily[d].append(v)

    result = {}
    for d, vals in daily.items():
        if not vals:
            continue
        if method == 'MAX':
            result[d] = max(vals)
        elif method == 'AVG':
            result[d] = sum(vals) / len(vals)
        elif method == 'SUM':
            result[d] = sum(vals)
    return result


def main():
    start_date = date(2024, 10, 28)
    end_date   = date.today() - timedelta(days=1)  # up to yesterday (closed days)

    print(f'Backfill wc_ema: {start_date} → {end_date}')
    print(f'Sensores EMA: {len(EMA_SENSORS)}')
    print()

    # Fetch all sensors, build {date: {col: value}}
    daily_data = defaultdict(dict)

    for sensor_id, (col, method) in EMA_SENSORS.items():
        print(f'Fetching {col} ({sensor_id}) [{method}] ...')
        cursor = start_date
        all_records = []

        while cursor <= end_date:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS - 1), end_date)
            records = fetch_sensor_month(sensor_id, cursor, chunk_end)
            all_records.extend(records)
            print(f'  {cursor} → {chunk_end}: {len(records)} registros')
            cursor = chunk_end + timedelta(days=1)
            time.sleep(0.3)  # gentle rate limiting

        agg = aggregate_daily(all_records, method)
        for d, v in agg.items():
            daily_data[d][col] = v

        print(f'  → {len(agg)} días con datos\n')

    # Upsert into wc_ema
    print(f'Upserting {len(daily_data)} días en wc_ema ...')

    conn = psycopg2.connect(**DB_CONNECT_KWARGS)
    cur  = conn.cursor()

    upsert_sql = """
        INSERT INTO wc_ema (
            date, farm_id, field,
            temperatura_c, humedad_relativa_pct, presion_atmosferica_pa,
            radiacion_solar_wm2, pluviometria_mm,
            velocidad_viento_kmh, rafaga_viento_kmh, direccion_viento_deg
        ) VALUES (
            %(date)s, %(farm_id)s, %(field)s,
            %(temperatura_c)s, %(humedad_relativa_pct)s, %(presion_atmosferica_pa)s,
            %(radiacion_solar_wm2)s, %(pluviometria_mm)s,
            %(velocidad_viento_kmh)s, %(rafaga_viento_kmh)s, %(direccion_viento_deg)s
        )
        ON CONFLICT (date, farm_id) DO UPDATE SET
            field                  = EXCLUDED.field,
            temperatura_c          = EXCLUDED.temperatura_c,
            humedad_relativa_pct   = EXCLUDED.humedad_relativa_pct,
            presion_atmosferica_pa = EXCLUDED.presion_atmosferica_pa,
            radiacion_solar_wm2    = EXCLUDED.radiacion_solar_wm2,
            pluviometria_mm        = EXCLUDED.pluviometria_mm,
            velocidad_viento_kmh   = EXCLUDED.velocidad_viento_kmh,
            rafaga_viento_kmh      = EXCLUDED.rafaga_viento_kmh,
            direccion_viento_deg   = EXCLUDED.direccion_viento_deg
    """

    rows = []
    for d in sorted(daily_data.keys()):
        row = daily_data[d]
        rows.append({
            'date':                  d,
            'farm_id':               FARM_ID,
            'field':                 FIELD,
            'temperatura_c':         row.get('temperatura_c'),
            'humedad_relativa_pct':  row.get('humedad_relativa_pct'),
            'presion_atmosferica_pa':row.get('presion_atmosferica_pa'),
            'radiacion_solar_wm2':   row.get('radiacion_solar_wm2'),
            'pluviometria_mm':       row.get('pluviometria_mm'),
            'velocidad_viento_kmh':  row.get('velocidad_viento_kmh'),
            'rafaga_viento_kmh':     row.get('rafaga_viento_kmh'),
            'direccion_viento_deg':  row.get('direccion_viento_deg'),
        })

    psycopg2.extras.execute_batch(cur, upsert_sql, rows, page_size=100)
    conn.commit()
    cur.close()
    conn.close()

    print(f'Backfill completado: {len(rows)} días upserted.')


if __name__ == '__main__':
    main()
