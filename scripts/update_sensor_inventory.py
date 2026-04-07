"""
Rebuilds sensor_inventory table — a full catalog of every sensor from both
Wiseconn and Ubibot, with last known value, last seen date, and status.

Status logic:
  ok      — last_seen within 2 days
  warning — last_seen 3–7 days ago
  offline — last_seen more than 7 days ago (or never)

Run:
  DATABASE_URL=... python scripts/update_sensor_inventory.py
"""

import os
import psycopg2

DB_URL = os.environ["DATABASE_URL"]


def connect():
    return psycopg2.connect(DB_URL)


def status_from_date(last_seen, today):
    if last_seen is None:
        return "offline"
    delta = (today - last_seen).days
    if delta <= 2:
        return "ok"
    if delta <= 7:
        return "warning"
    return "offline"


def upsert(cur, rows):
    cur.executemany("""
        INSERT INTO sensor_inventory
            (source, field, zone, orchard, sensor_id, sensor_name, unit,
             last_value, last_seen, status, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (source, sensor_id, sensor_name) DO UPDATE SET
            field      = EXCLUDED.field,
            zone       = EXCLUDED.zone,
            orchard    = EXCLUDED.orchard,
            unit       = EXCLUDED.unit,
            last_value = EXCLUDED.last_value,
            last_seen  = EXCLUDED.last_seen,
            status     = EXCLUDED.status,
            updated_at = NOW()
    """, rows)


def fetch_wiseconn(cur, today):
    cur.execute("""
        WITH latest AS (
            SELECT DISTINCT ON (farm_id, zone_id, sensor_id)
                farm_id, zone_id, sensor_id, name, unit, values, date
            FROM wc_zones_sensors
            ORDER BY farm_id, zone_id, sensor_id, date DESC
        )
        SELECT
            CASE WHEN s.farm_id = '14245' THEN 'ZUÑIGA' ELSE 'ISLA DE MAIPO' END AS field,
            z.name  AS zone,
            fs.orchard,
            s.sensor_id,
            s.name  AS sensor_name,
            s.unit,
            s.values,
            s.date  AS last_seen
        FROM latest s
        JOIN wc_farms_zones z
            ON CAST(NULLIF(s.zone_id, 'NaN') AS numeric)::integer = z.id
        LEFT JOIN field_sectors fs
            ON CAST(NULLIF(s.zone_id, 'NaN') AS numeric)::integer = fs.wc_zone_id
        ORDER BY field, zone, sensor_name
    """)
    rows = []
    for r in cur.fetchall():
        field, zone, orchard, sensor_id, sensor_name, unit, last_value, last_seen = r
        rows.append((
            'wiseconn', field, zone, orchard,
            sensor_id, sensor_name, unit,
            round(float(last_value), 4) if last_value is not None else None,
            last_seen,
            status_from_date(last_seen, today),
        ))
    return rows


def fetch_ubibot(cur, today):
    # One row per channel+sensor_name using DISTINCT ON for performance
    cur.execute("""
        WITH latest AS (
            SELECT DISTINCT ON (channel_id, name)
                channel_id, name, avg, date
            FROM ubi_channels_fields
            ORDER BY channel_id, name, date DESC
        )
        SELECT DISTINCT ON (u.channel_id, u.name)
            COALESCE(fs.field, 'unassigned')  AS field,
            ucd.name                           AS zone,
            fs.orchard,
            u.channel_id::text                 AS sensor_id,
            u.name                             AS sensor_name,
            NULL::text                         AS unit,
            u.avg                              AS last_value,
            u.date                             AS last_seen
        FROM latest u
        JOIN ubi_channel_data ucd ON u.channel_id = ucd.channel_id
        LEFT JOIN field_sectors fs ON u.channel_id = ANY(fs.ubibot_channel_ids)
        ORDER BY u.channel_id, u.name, fs.field NULLS LAST
    """)
    rows = []
    for r in cur.fetchall():
        field, zone, orchard, sensor_id, sensor_name, unit, last_value, last_seen = r
        rows.append((
            'ubibot', field, zone, orchard,
            sensor_id, sensor_name, unit,
            round(float(last_value), 4) if last_value is not None else None,
            last_seen,
            status_from_date(last_seen, today),
        ))
    return rows


def run():
    from datetime import date
    today = date.today()

    conn = connect()
    cur = conn.cursor()

    wc_rows = fetch_wiseconn(cur, today)
    ubi_rows = fetch_ubibot(cur, today)

    upsert(cur, wc_rows + ubi_rows)
    conn.commit()
    conn.close()

    print(f"sensor_inventory updated: {len(wc_rows)} wiseconn + {len(ubi_rows)} ubibot = {len(wc_rows)+len(ubi_rows)} rows.")


if __name__ == "__main__":
    run()
