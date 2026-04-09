"""
Backfill Et0 and Etc in wc_zones_sensors using the correct daily accumulation
from Wiseconn's /measures/{id}/data endpoint.

The regular pipeline uses lastData which resets at 00:00 UTC (21:00 Santiago),
causing all runs after that time to record 0 for the day in progress.
This script fetches the closed daily value for each past date and corrects it.

Usage:
    DATABASE_URL=... API_KEY=... python scripts/backfill_et0_etc.py
    DATABASE_URL=... API_KEY=... python scripts/backfill_et0_etc.py --from 2026-01-01 --to 2026-04-09
"""

import os
import sys
import argparse
import datetime
import time

import requests
import psycopg2

DB_URL = os.environ["DATABASE_URL"]
API_KEY = os.environ["API_KEY"]
BASE_URL = "https://api.wiseconn.com"
HEADERS = {"api_key": API_KEY}

# All Et0/Etc sensor_ids with their zone_id and farm_id
SENSORS = [
    # Et0
    {"sensor_id": "6-53361-1",  "name": "Et0", "unit": "mm", "zone_id": "53361.0",  "farm_id": "14245"},
    {"sensor_id": "6-53367-1",  "name": "Et0", "unit": "mm", "zone_id": "53367.0",  "farm_id": "14245"},
    {"sensor_id": "6-155231-1", "name": "Et0", "unit": "mm", "zone_id": "155231.0", "farm_id": "60544"},
    # Etc Zuñiga
    {"sensor_id": "6-50918-2",  "name": "Etc", "unit": "mm", "zone_id": "50918.0",  "farm_id": "14245"},
    {"sensor_id": "6-50919-2",  "name": "Etc", "unit": "mm", "zone_id": "50919.0",  "farm_id": "14245"},
    {"sensor_id": "6-50922-2",  "name": "Etc", "unit": "mm", "zone_id": "50922.0",  "farm_id": "14245"},
    {"sensor_id": "6-50924-2",  "name": "Etc", "unit": "mm", "zone_id": "50924.0",  "farm_id": "14245"},
    {"sensor_id": "6-50925-2",  "name": "Etc", "unit": "mm", "zone_id": "50925.0",  "farm_id": "14245"},
    {"sensor_id": "6-50927-2",  "name": "Etc", "unit": "mm", "zone_id": "50927.0",  "farm_id": "14245"},
    {"sensor_id": "6-50928-2",  "name": "Etc", "unit": "mm", "zone_id": "50928.0",  "farm_id": "14245"},
    {"sensor_id": "6-50929-2",  "name": "Etc", "unit": "mm", "zone_id": "50929.0",  "farm_id": "14245"},
    {"sensor_id": "6-50930-2",  "name": "Etc", "unit": "mm", "zone_id": "50930.0",  "farm_id": "14245"},
    {"sensor_id": "6-50931-2",  "name": "Etc", "unit": "mm", "zone_id": "50931.0",  "farm_id": "14245"},
    {"sensor_id": "6-50932-2",  "name": "Etc", "unit": "mm", "zone_id": "50932.0",  "farm_id": "14245"},
    {"sensor_id": "6-50933-2",  "name": "Etc", "unit": "mm", "zone_id": "50933.0",  "farm_id": "14245"},
    {"sensor_id": "6-50934-2",  "name": "Etc", "unit": "mm", "zone_id": "50934.0",  "farm_id": "14245"},
    {"sensor_id": "6-53361-2",  "name": "Etc", "unit": "mm", "zone_id": "53361.0",  "farm_id": "14245"},
    {"sensor_id": "6-53367-2",  "name": "Etc", "unit": "mm", "zone_id": "53367.0",  "farm_id": "14245"},
    # Etc Isla de Maipo
    {"sensor_id": "6-114938-2", "name": "Etc", "unit": "mm", "zone_id": "114938.0", "farm_id": "60544"},
    {"sensor_id": "6-114939-2", "name": "Etc", "unit": "mm", "zone_id": "114939.0", "farm_id": "60544"},
    {"sensor_id": "6-114940-2", "name": "Etc", "unit": "mm", "zone_id": "114940.0", "farm_id": "60544"},
    {"sensor_id": "6-114941-2", "name": "Etc", "unit": "mm", "zone_id": "114941.0", "farm_id": "60544"},
    {"sensor_id": "6-114942-2", "name": "Etc", "unit": "mm", "zone_id": "114942.0", "farm_id": "60544"},
    {"sensor_id": "6-114943-2", "name": "Etc", "unit": "mm", "zone_id": "114943.0", "farm_id": "60544"},
    {"sensor_id": "6-114944-2", "name": "Etc", "unit": "mm", "zone_id": "114944.0", "farm_id": "60544"},
    {"sensor_id": "6-114945-2", "name": "Etc", "unit": "mm", "zone_id": "114945.0", "farm_id": "60544"},
    {"sensor_id": "6-155231-2", "name": "Etc", "unit": "mm", "zone_id": "155231.0", "farm_id": "60544"},
]

UPSERT_SQL = """
    INSERT INTO wc_zones_sensors (sensor_id, name, unit, values, created_at, date, hour, zone_id, farm_id)
    VALUES (%(sensor_id)s, %(name)s, %(unit)s, %(values)s, %(created_at)s, %(date)s, %(hour)s, %(zone_id)s, %(farm_id)s)
    ON CONFLICT (date, sensor_id, zone_id) DO UPDATE
        SET values     = EXCLUDED.values,
            created_at = EXCLUDED.created_at,
            hour       = EXCLUDED.hour
        WHERE wc_zones_sensors.values = 0 OR wc_zones_sensors.values IS NULL;
"""


def fetch_sensor_history(sensor_id, date_from, date_to):
    """Fetch daily values from Wiseconn /measures/{id}/data."""
    r = requests.get(
        f"{BASE_URL}/measures/{sensor_id}/data",
        headers=HEADERS,
        params={"initTime": date_from.strftime("%Y-%m-%d"),
                "endTime":   date_to.strftime("%Y-%m-%d")},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()  # [{time, value}, ...]


def run(date_from, date_to):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    total_updated = 0
    total_skipped = 0

    for sensor in SENSORS:
        sid = sensor["sensor_id"]
        print(f"\n→ {sid} ({sensor['name']} zone {sensor['zone_id']} farm {sensor['farm_id']})")

        try:
            records = fetch_sensor_history(sid, date_from, date_to)
        except Exception as e:
            print(f"  ERROR fetching: {e}")
            continue

        time.sleep(0.2)  # light rate limiting

        updated = 0
        for rec in records:
            raw_time = rec.get("time")
            value = rec.get("value")

            if raw_time is None or value is None:
                continue

            # Wiseconn timestamps are UTC 00:00 — treat as the closed daily value
            import datetime as dt
            ts = dt.datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            record_date = ts.date()

            # Only process dates within range (exclude today — still accumulating)
            if record_date < date_from or record_date >= date_to:
                continue

            row = {
                "sensor_id":  sid,
                "name":       sensor["name"],
                "unit":       sensor["unit"],
                "values":     value,
                "created_at": ts.replace(tzinfo=None),  # store naive, Santiago convention
                "date":       record_date,
                "hour":       ts.time(),
                "zone_id":    sensor["zone_id"],
                "farm_id":    sensor["farm_id"],
            }
            cur.execute(UPSERT_SQL, row)
            if cur.rowcount > 0:
                updated += 1
            else:
                total_skipped += 1

        conn.commit()
        total_updated += updated
        print(f"  {updated} rows updated, {len(records)} fetched from API")

    cur.close()
    conn.close()
    print(f"\nDone — {total_updated} rows updated, {total_skipped} already had correct values.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from", default="2026-01-01",
                        help="Start date inclusive (default: 2026-01-01)")
    parser.add_argument("--to", dest="date_to",
                        default=datetime.date.today().strftime("%Y-%m-%d"),
                        help="End date exclusive (default: today)")
    args = parser.parse_args()

    date_from = datetime.date.fromisoformat(args.date_from)
    date_to   = datetime.date.fromisoformat(args.date_to)

    print(f"Backfilling Et0/Etc from {date_from} to {date_to} (exclusive)")
    print(f"Sensors: {len(SENSORS)}")
    run(date_from, date_to)
