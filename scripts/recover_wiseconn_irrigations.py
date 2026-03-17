"""
Recovers missing wc_farms_realirrigation and wc_farms_irrigation data
for all gap periods where the pipeline didn't run.

Only these two tables are recoverable from Wiseconn — they store events
with real timestamps. wc_zones_sensors is a snapshot table (latest value only)
so historical sensor readings cannot be recovered.

Usage:
    API_KEY=... DATABASE_URL=... python scripts/recover_wiseconn_irrigations.py
"""

import os
import time
import requests
import psycopg2
import psycopg2.extras
from datetime import date, timedelta, datetime

API_KEY = os.environ["API_KEY"]
DB_URL = os.environ["DATABASE_URL"]
FARM_IDS = [14245, 60544]

# All gap periods identified from execution_log
GAP_PERIODS = [
    ("2024-06-09", "2024-07-22"),
    ("2024-10-04", "2024-10-12"),
    ("2024-12-26", "2024-12-26"),
    ("2025-05-22", "2025-05-22"),
    ("2025-06-11", "2025-06-17"),
    ("2025-06-22", "2025-06-22"),
    ("2025-07-29", "2025-08-10"),
    ("2025-09-13", "2025-10-02"),
]

HEADERS = {"api_key": API_KEY}


def fetch_real_irrigations(farm_id, start, end):
    url = f"https://api.wiseconn.com/farms/{farm_id}/realIrrigations"
    resp = requests.get(url, headers=HEADERS, params={"initTime": start, "endTime": end}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_irrigations(farm_id, start, end):
    url = f"https://api.wiseconn.com/farms/{farm_id}/irrigations"
    resp = requests.get(url, headers=HEADERS, params={"initTime": start, "endTime": end}, timeout=60)
    resp.raise_for_status()
    return resp.json()


def parse_real_irrigations(data, farm_id):
    rows = []
    for item in data:
        try:
            init_time = datetime.fromisoformat(item["initTime"].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(item["endTime"].replace("Z", "+00:00")) if item.get("endTime") else None

            # Strip timezone — store as naive Chile time (API returns UTC, convert)
            from datetime import timezone
            init_naive = init_time.astimezone(timezone.utc).replace(tzinfo=None)
            end_naive = end_time.astimezone(timezone.utc).replace(tzinfo=None) if end_time else None

            vol = item.get("volume", {})
            prec = item.get("precipitation", {})
            flow = item.get("flow", {})
            iflow = item.get("instantaneousFlow", {})

            rows.append({
                "created_at": init_naive,
                "date": init_naive.date(),
                "hour": init_naive.time(),
                "init_time": init_naive,
                "end_time": end_naive,
                "delta_time": str(end_naive - init_naive) if end_naive else None,
                "zone_id": item.get("zoneId"),
                "status": item.get("status"),
                "pump_system_id": item.get("pumpSystemId"),
                "scheduled_irrigation_id": item.get("scheduledIrrigationId"),
                "volume_m3": vol.get("value"),
                "precipitation_mm": prec.get("value"),
                "flow_m3_h": flow.get("value"),
                "instantaneous_flow_m3_h": iflow.get("value"),
                "pressure": None,
                "measures": psycopg2.extras.Json(item.get("measures")),
                "farm_id": farm_id,
            })
        except Exception as e:
            print(f"    [WARN] parse error: {e}")
    return rows


def parse_irrigations(data, farm_id):
    rows = []
    for item in data:
        try:
            init_time = datetime.fromisoformat(item["initTime"].replace("Z", "+00:00"))
            end_time = datetime.fromisoformat(item["endTime"].replace("Z", "+00:00")) if item.get("endTime") else None

            from datetime import timezone
            init_naive = init_time.astimezone(timezone.utc).replace(tzinfo=None)
            end_naive = end_time.astimezone(timezone.utc).replace(tzinfo=None) if end_time else None

            vol = item.get("volume", {})
            prec = item.get("precipitation", {})
            tflow = item.get("theoricalFlow", {})

            rows.append({
                "created_at": init_naive,
                "date": init_naive.date(),
                "hour": init_naive.time(),
                "inittime": init_naive,
                "endtime": end_naive,
                "delta_time": str(end_naive - init_naive) if end_naive else None,
                "status": item.get("status"),
                "irrigationtype": (item.get("type") or {}).get("description"),
                "pumpsystemid": item.get("pumpSystemId"),
                "pumpids": str(item.get("pumpIds")) if item.get("pumpIds") else None,
                "zone_id": item.get("zoneId"),
                "senttonetwork": item.get("sentToNetwork"),
                "scheduledtype": (item.get("scheduledType") or {}).get("description") if isinstance(item.get("scheduledType"), dict) else item.get("scheduledType"),
                "hydraulics": None,
                "groupingname": item.get("groupingName"),
                "volume_m3": vol.get("value"),
                "precipitation_mm": prec.get("value"),
                "theoreticalflow_m3_h": tflow.get("value"),
                "farm_id": farm_id,
            })
        except Exception as e:
            print(f"    [WARN] parse error: {e}")
    return rows


def upsert_real_irrigations(conn, rows):
    if not rows:
        return 0
    sql = """
        INSERT INTO wc_farms_realirrigation
            (created_at, date, hour, init_time, end_time, delta_time, zone_id, status,
             pump_system_id, scheduled_irrigation_id, volume_m3, precipitation_mm,
             flow_m3_h, instantaneous_flow_m3_h, pressure, measures, farm_id)
        VALUES
            (%(created_at)s, %(date)s, %(hour)s, %(init_time)s, %(end_time)s, %(delta_time)s,
             %(zone_id)s, %(status)s, %(pump_system_id)s, %(scheduled_irrigation_id)s,
             %(volume_m3)s, %(precipitation_mm)s, %(flow_m3_h)s, %(instantaneous_flow_m3_h)s,
             %(pressure)s, %(measures)s, %(farm_id)s)
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=200)
    conn.commit()
    return len(rows)


def upsert_irrigations(conn, rows):
    if not rows:
        return 0
    sql = """
        INSERT INTO wc_farms_irrigation
            (created_at, date, hour, inittime, endtime, delta_time, status, irrigationtype,
             pumpsystemid, pumpids, zone_id, senttonetwork, scheduledtype, hydraulics,
             groupingname, volume_m3, precipitation_mm, theoreticalflow_m3_h, farm_id)
        VALUES
            (%(created_at)s, %(date)s, %(hour)s, %(inittime)s, %(endtime)s, %(delta_time)s,
             %(status)s, %(irrigationtype)s, %(pumpsystemid)s, %(pumpids)s, %(zone_id)s,
             %(senttonetwork)s, %(scheduledtype)s, %(hydraulics)s, %(groupingname)s,
             %(volume_m3)s, %(precipitation_mm)s, %(theoreticalflow_m3_h)s, %(farm_id)s)
        ON CONFLICT DO NOTHING
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=200)
    conn.commit()
    return len(rows)


def date_chunks(start_str, end_str, days=7):
    """Split a date range into chunks of N days."""
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)
    chunk = timedelta(days=days)
    d = start
    while d <= end:
        yield str(d), str(min(d + chunk - timedelta(days=1), end))
        d += chunk


def main():
    conn = psycopg2.connect(DB_URL)
    total_real = 0
    total_irr = 0

    for start_str, end_str in GAP_PERIODS:
        print(f"\n--- Gap: {start_str} → {end_str} ---")

        for chunk_start, chunk_end in date_chunks(start_str, end_str):
            for farm_id in FARM_IDS:
                try:
                    # Real irrigations
                    data = fetch_real_irrigations(farm_id, chunk_start, chunk_end)
                    rows = parse_real_irrigations(data, farm_id)
                    n = upsert_real_irrigations(conn, rows)
                    total_real += n
                    if n > 0:
                        print(f"  {chunk_start}→{chunk_end} farm {farm_id} realIrrigations: {n} upserted")

                    time.sleep(1)

                    # Scheduled irrigations
                    data = fetch_irrigations(farm_id, chunk_start, chunk_end)
                    rows = parse_irrigations(data, farm_id)
                    n = upsert_irrigations(conn, rows)
                    total_irr += n
                    if n > 0:
                        print(f"  {chunk_start}→{chunk_end} farm {farm_id} irrigations:     {n} upserted")

                    time.sleep(1)

                except Exception as e:
                    print(f"  {chunk_start}→{chunk_end} farm {farm_id} ERROR: {e}")
                    conn.rollback()

    conn.close()
    print(f"\nDone. Total upserted — realIrrigations: {total_real}, irrigations: {total_irr}")


if __name__ == "__main__":
    main()
