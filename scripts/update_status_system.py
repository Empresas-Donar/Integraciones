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
    """Total riego_mm per day per field. Also counts events with zero mm."""
    cur.execute("""
        SELECT
            r.date,
            fs.field,
            ROUND(SUM(r.precipitation_mm)::numeric, 1)              AS riego_mm,
            COUNT(*) FILTER (WHERE r.precipitation_mm > 0)          AS events_with_mm,
            COUNT(*) FILTER (WHERE r.precipitation_mm = 0)          AS events_zero_mm,
            ROUND(SUM(EXTRACT(EPOCH FROM r.delta_time)/3600)::numeric, 1) AS total_hours
        FROM wc_farms_realirrigation r
        JOIN field_sectors fs ON fs.farm_id = r.farm_id
        WHERE r.date >= %s
        GROUP BY r.date, fs.field
    """, (since,))
    result = {}
    for r in cur.fetchall():
        result[(r[0], r[1])] = {
            "riego_mm": r[2],
            "events_with_mm": r[3],
            "events_zero_mm": r[4],
            "total_hours": r[5],
        }
    return result


def build_notes(ubi, irr, exec_row, expected_channels):
    """Generate automatic notes based on anomalies detected."""
    notes = []

    # Irrigation executed but no mm recorded
    if irr:
        if irr["events_zero_mm"] > 0 and irr["events_with_mm"] == 0:
            notes.append(
                f"Riego ejecutado ({irr['total_hours']}h) sin mm registrados — "
                f"caudalímetros sin datos en Wiseconn"
            )
        elif irr["events_zero_mm"] > 0:
            notes.append(
                f"{irr['events_zero_mm']} eventos de riego sin mm medidos"
            )

    # Ubibot channels below threshold
    if ubi:
        canales = ubi.get("canales", 0)
        green_threshold = max(1, round(expected_channels * 0.8))
        if 0 < canales < green_threshold:
            notes.append(
                f"Ubibot: {canales}/{expected_channels} canales activos"
            )
        elif canales == 0:
            notes.append("Ubibot: sin canales activos")

    # Execution failures
    if exec_row:
        total = exec_row["total"]
        if exec_row["wc_ok"] < total:
            failed = total - exec_row["wc_ok"]
            notes.append(f"Wiseconn: {failed}/{total} ejecuciones fallidas")
        if exec_row["ubi_ok"] < total:
            failed = total - exec_row["ubi_ok"]
            notes.append(f"Ubibot sync: {failed}/{total} ejecuciones fallidas")
    elif exec_row is None:
        notes.append("Sin ejecuciones registradas")

    return "; ".join(notes) if notes else None


def compute_status(exec_row, ubibot_channels, expected_channels):
    """
    status = 'ok' | 'partial' | 'error'
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
    channels_ok = (ubibot_channels >= green_threshold)

    if executions_ok and channels_ok:
        return "ok"
    if wc_ok == 0 and ubi_ok == 0 and ubibot_channels < yellow_threshold:
        return "error"
    return "partial"


def upsert_row(cur, date_, field, status, wc_executions, ubibot_channels,
               temp_avg, temp_min, temp_max, irrigation_mm, notes):
    cur.execute("""
        INSERT INTO status_system
            (date, field, status, wc_executions, ubibot_channels,
             temp_avg, temp_min, temp_max, irrigation_mm, notes, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (date, field) DO UPDATE SET
            status          = EXCLUDED.status,
            wc_executions   = EXCLUDED.wc_executions,
            ubibot_channels = EXCLUDED.ubibot_channels,
            temp_avg        = EXCLUDED.temp_avg,
            temp_min        = EXCLUDED.temp_min,
            temp_max        = EXCLUDED.temp_max,
            irrigation_mm   = EXCLUDED.irrigation_mm,
            notes           = EXCLUDED.notes,
            updated_at      = NOW()
    """, (date_, field, status, wc_executions, ubibot_channels,
          temp_avg, temp_min, temp_max, irrigation_mm, notes))


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
        wc_executions = f"{exec_row['wc_ok']}/{exec_row['total']}" if exec_row else None

        for field, _farm_id, expected_channels in fields:
            ubi = ubi_stats.get((d, field), {})
            channels = ubi.get("canales", 0)
            irr = irr_data.get((d, field))
            status = compute_status(exec_row, channels, expected_channels)
            notes = build_notes(ubi, irr, exec_row, expected_channels)

            upsert_row(
                cur, d, field,
                status,
                wc_executions,
                channels or None,
                ubi.get("temp_avg"),
                ubi.get("temp_min"),
                ubi.get("temp_max"),
                irr["riego_mm"] if irr and irr["riego_mm"] else None,
                notes,
            )
            rows_written += 1

    conn.commit()
    conn.close()
    print(f"status_system updated: {rows_written} rows upserted (last {DAYS_BACK} days).")


if __name__ == "__main__":
    run()
