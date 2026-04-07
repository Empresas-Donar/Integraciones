"""
Fills the status_system table with the last 15 days of operational data,
one row per day per field (campo).

Columns:
  fecha           — date
  campo           — field name (from field_sectors.field), scales automatically
  sistema         — 'ok' | 'partial' | 'error'
  wc_ejecuciones  — 'ok/total' executions that day
  ubibot_canales  — distinct active Ubibot channels that day (assigned to this field)
  temp_avg/min/max — ambient temperature from Ubibot sensors assigned to this field
  riego_mm        — total precipitation_mm for this field that day

Run:
  DATABASE_URL=... python scripts/update_status_system.py
"""

import os
import psycopg2
from datetime import date, timedelta

DB_URL = os.environ["DATABASE_URL"]

DAYS_BACK = 15
UBIBOT_GREEN_THRESHOLD = 10
UBIBOT_YELLOW_THRESHOLD = 5


def connect():
    return psycopg2.connect(DB_URL)


def fetch_fields(cur):
    """Return list of (field, farm_id, channel_count) from field_sectors."""
    cur.execute("""
        SELECT field, farm_id,
               COUNT(DISTINCT ch) AS channel_count
        FROM field_sectors,
             LATERAL unnest(ubibot_channel_ids) AS ch
        GROUP BY field, farm_id
        ORDER BY field
    """)
    return cur.fetchall()  # (field, farm_id, channel_count)


def fetch_execution_summary(cur, since):
    """Executions per day (global — not per field, Wiseconn covers all farms per run)."""
    cur.execute("""
        SELECT
            date::date AS fecha,
            COUNT(*) AS total,
            SUM(CASE WHEN status_wiseconn = 'Success' THEN 1 ELSE 0 END) AS wc_ok,
            SUM(CASE WHEN status_ubibot   = 'Success' THEN 1 ELSE 0 END) AS ubi_ok
        FROM execution_log
        WHERE date >= %s
        GROUP BY date::date
    """, (since,))
    return {r[0]: {"total": r[1], "wc_ok": r[2], "ubi_ok": r[3]} for r in cur.fetchall()}


def fetch_ubibot_stats_per_field(cur, since):
    """
    Active channels and temperature stats per day per field.
    Only counts channels assigned to each field via field_sectors.ubibot_channel_ids.
    """
    cur.execute("""
        SELECT
            u.date,
            fs.field,
            COUNT(DISTINCT u.channel_id)             AS canales,
            ROUND(AVG(u.avg)::numeric, 1)            AS temp_avg,
            ROUND(MIN(u.min)::numeric, 1)            AS temp_min,
            ROUND(MAX(u.max)::numeric, 1)            AS temp_max
        FROM ubi_channels_fields u
        JOIN (
            SELECT DISTINCT field, unnest(ubibot_channel_ids) AS channel_id
            FROM field_sectors
        ) fs ON u.channel_id = fs.channel_id
        WHERE u.name = 'Temperature'
          AND u.date >= %s
        GROUP BY u.date, fs.field
    """, (since,))
    result = {}
    for row in cur.fetchall():
        result[(row[0], row[1])] = {
            "canales": row[2],
            "temp_avg": row[3],
            "temp_min": row[4],
            "temp_max": row[5],
        }
    return result


def fetch_irrigation_per_field(cur, since):
    """Total riego_mm per day per field."""
    cur.execute("""
        SELECT
            r.date,
            fs.field,
            ROUND(SUM(r.precipitation_mm)::numeric, 1) AS riego_mm
        FROM wc_farms_realirrigation r
        JOIN field_sectors fs ON fs.farm_id = r.farm_id
        WHERE r.date >= %s
          AND r.precipitation_mm > 0
        GROUP BY r.date, fs.field
    """, (since,))
    return {(r[0], r[1]): r[2] for r in cur.fetchall()}


def compute_sistema(exec_row, ubibot_canales, expected_channels):
    """
    sistema = 'ok' | 'partial' | 'error'
    Ubibot threshold is relative to the channels assigned to this field
    (so Isla de Maipo with 1 channel assigned is not penalized).
    """
    if exec_row is None:
        return "error"
    total = exec_row["total"]
    wc_ok = exec_row["wc_ok"]
    ubi_ok = exec_row["ubi_ok"]
    if total == 0:
        return "error"

    # Per-field thresholds: green if >= 80% of assigned channels, yellow if >= 40%
    green_threshold = max(1, round(expected_channels * 0.8))
    yellow_threshold = max(1, round(expected_channels * 0.4))

    executions_ok = (wc_ok == total and ubi_ok == total)
    channels_ok = (ubibot_canales >= green_threshold)

    if executions_ok and channels_ok:
        return "ok"
    if wc_ok == 0 and ubi_ok == 0 and ubibot_canales < yellow_threshold:
        return "error"
    return "partial"


def upsert_row(cur, fecha, campo, sistema, wc_ejecuciones, ubibot_canales,
               temp_avg, temp_min, temp_max, riego_mm):
    cur.execute("""
        INSERT INTO status_system
            (fecha, campo, sistema, wc_ejecuciones, ubibot_canales,
             temp_avg, temp_min, temp_max, riego_mm, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (fecha, campo) DO UPDATE SET
            sistema        = EXCLUDED.sistema,
            wc_ejecuciones = EXCLUDED.wc_ejecuciones,
            ubibot_canales = EXCLUDED.ubibot_canales,
            temp_avg       = EXCLUDED.temp_avg,
            temp_min       = EXCLUDED.temp_min,
            temp_max       = EXCLUDED.temp_max,
            riego_mm       = EXCLUDED.riego_mm,
            updated_at     = NOW()
    """, (fecha, campo, sistema, wc_ejecuciones, ubibot_canales,
          temp_avg, temp_min, temp_max, riego_mm))


def run():
    since = date.today() - timedelta(days=DAYS_BACK)
    conn = connect()
    cur = conn.cursor()

    fields = fetch_fields(cur)
    exec_data = fetch_execution_summary(cur, since)
    ubi_stats = fetch_ubibot_stats_per_field(cur, since)
    irr_data = fetch_irrigation_per_field(cur, since)

    rows_written = 0
    for d_offset in range(DAYS_BACK + 1):
        d = since + timedelta(days=d_offset)
        if d > date.today():
            break

        exec_row = exec_data.get(d)
        wc_ejecuciones = f"{exec_row['wc_ok']}/{exec_row['total']}" if exec_row else None

        for campo, _farm_id, expected_channels in fields:
            ubi = ubi_stats.get((d, campo), {})
            canales = ubi.get("canales", 0)
            sistema = compute_sistema(exec_row, canales, expected_channels)

            upsert_row(
                cur, d, campo,
                sistema,
                wc_ejecuciones,
                canales or None,
                ubi.get("temp_avg"),
                ubi.get("temp_min"),
                ubi.get("temp_max"),
                irr_data.get((d, campo)),
            )
            rows_written += 1

    conn.commit()
    conn.close()
    print(f"status_system updated: {rows_written} rows upserted (last {DAYS_BACK} days).")


if __name__ == "__main__":
    run()
