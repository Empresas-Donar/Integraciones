"""
Backfill wc_ema with correct daily aggregates from the Wiseconn API.

The pipeline stores only the last value per day (midnight snapshot), which is
always 0 for daytime sensors like solar radiation and wind speed. This script
fetches the full 15-minute time series per sensor and computes the correct
daily aggregate (MAX for instantaneous sensors, AVG for continuous ones).

Aggregation strategy:
  - Temperatura         → AVG  (mean temperature for the day)
  - Humedad Relativa    → AVG
  - Presión Atmosférica → AVG
  - Radiacion Solar     → MAX  (peak radiation)
  - Pluviometría        → MAX  (daily accumulated total, already cumulative)
  - Velocidad Viento    → AVG  (mean wind speed)
  - Rafaga Viento       → MAX  (peak gust)
  - Dirección Viento    → AVG  (mean direction — simplification, valid for unimodal wind)

Farms:
  - 14245 ZUÑIGA       — sensors named "* - EMA"    — data from 2024-10-28
  - 60544 ISLA DE MAIPO — sensors named "* Davis API" — data from 2025-04-01
"""

import os
import sys
import time
import requests
import psycopg2
import psycopg2.extras
from datetime import date, timedelta, datetime
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
BASE_URL   = 'https://api.wiseconn.com'
CHUNK_DAYS = 30

FARMS = [
    {
        'farm_id': '14245',
        'field':   'ZUÑIGA',
        'start':   date(2024, 10, 28),
        'sensors': {
            '1-214559': ('radiacion_solar_wm2',    'MAX'),
            '1-214560': ('humedad_relativa_pct',   'AVG'),
            '1-214561': ('pluviometria_mm',        'MAX'),
            '1-214562': ('velocidad_viento_kmh',   'AVG'),
            '1-214563': ('temperatura_c',          'AVG'),
            '1-214564': ('direccion_viento_deg',   'AVG'),
            '1-214565': ('rafaga_viento_kmh',      'MAX'),
            '1-214566': ('presion_atmosferica_pa', 'AVG'),
        },
    },
    {
        'farm_id': '60544',
        'field':   'ISLA DE MAIPO',
        'start':   date(2025, 4, 1),
        'sensors': {
            '1-404379': ('temperatura_c',          'AVG'),
            '1-404380': ('humedad_relativa_pct',   'AVG'),
            '1-404381': ('velocidad_viento_kmh',   'AVG'),
            '1-404382': ('radiacion_solar_wm2',    'MAX'),
            '1-404383': ('pluviometria_mm',        'MAX'),
            '1-404384': ('direccion_viento_deg',   'AVG'),
            '1-404385': ('presion_atmosferica_pa', 'AVG'),
            '1-404386': ('rafaga_viento_kmh',      'MAX'),
        },
    },
]

UPSERT_SQL = """
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


def fetch_sensor_chunk(sensor_id, start: date, end: date):
    params = {'initTime': start.strftime('%Y-%m-%d'), 'endTime': end.strftime('%Y-%m-%d')}
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
    """Group 15-min records by local date, apply aggregation, return {date: value}."""
    daily = defaultdict(list)
    for rec in records:
        t = datetime.fromisoformat(rec['time'].replace('Z', '+00:00'))
        d = t.astimezone(tz=None).date()
        v = rec.get('value')
        if v is not None:
            daily[d].append(v)
    result = {}
    for d, vals in daily.items():
        if not vals:
            continue
        result[d] = max(vals) if method == 'MAX' else sum(vals) / len(vals)
    return result


def backfill_farm(farm, end_date, cur):
    farm_id = farm['farm_id']
    field   = farm['field']
    start   = farm['start']
    sensors = farm['sensors']

    print(f'\n=== {field} (farm_id={farm_id}) ===')
    print(f'Período: {start} → {end_date}')

    daily_data = defaultdict(dict)

    for sensor_id, (col, method) in sensors.items():
        print(f'  Fetching {col} ({sensor_id}) [{method}] ...')
        cursor      = start
        all_records = []

        while cursor <= end_date:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS - 1), end_date)
            records   = fetch_sensor_chunk(sensor_id, cursor, chunk_end)
            all_records.extend(records)
            print(f'    {cursor} → {chunk_end}: {len(records)} registros')
            cursor = chunk_end + timedelta(days=1)
            time.sleep(0.3)

        agg = aggregate_daily(all_records, method)
        for d, v in agg.items():
            daily_data[d][col] = v
        print(f'  → {len(agg)} días con datos')

    rows = []
    for d in sorted(daily_data.keys()):
        row = daily_data[d]
        rows.append({
            'date':                   d,
            'farm_id':                farm_id,
            'field':                  field,
            'temperatura_c':          row.get('temperatura_c'),
            'humedad_relativa_pct':   row.get('humedad_relativa_pct'),
            'presion_atmosferica_pa': row.get('presion_atmosferica_pa'),
            'radiacion_solar_wm2':    row.get('radiacion_solar_wm2'),
            'pluviometria_mm':        row.get('pluviometria_mm'),
            'velocidad_viento_kmh':   row.get('velocidad_viento_kmh'),
            'rafaga_viento_kmh':      row.get('rafaga_viento_kmh'),
            'direccion_viento_deg':   row.get('direccion_viento_deg'),
        })

    print(f'  Upserting {len(rows)} días ...')
    psycopg2.extras.execute_batch(cur, UPSERT_SQL, rows, page_size=100)
    print(f'  ✓ {field} completado: {len(rows)} días upserted.')


def main():
    end_date = date.today() - timedelta(days=1)
    conn = psycopg2.connect(**DB_CONNECT_KWARGS)
    cur  = conn.cursor()

    for farm in FARMS:
        backfill_farm(farm, end_date, cur)
        conn.commit()

    cur.close()
    conn.close()
    print('\nBackfill completo.')


if __name__ == '__main__':
    main()
