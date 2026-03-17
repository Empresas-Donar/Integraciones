"""
Recovers missing ubi_channels_fields data for the gap period.

The bug: ON CONFLICT was missing from the INSERT, so any duplicate
(created_at, channel_id, name) caused a rollback of the entire batch.
This script fetches from the Ubibot API and writes directly to the DB
using the same logic as the pipeline but with upsert.

Usage:
    DATABASE_URL=... UBIBOT_ACCOUNT_KEY=... python scripts/recover_ubibot_fields.py
"""

import os
import time
import uuid
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import pytz

DB_URL = os.environ["DATABASE_URL"]
ACCOUNT_KEY = os.environ["UBIBOT_ACCOUNT_KEY"]
SANTIAGO = pytz.timezone("America/Santiago")

# Gap period to recover
START_DATE = "2026-02-26 00:00:00"
END_DATE   = datetime.now(SANTIAGO).strftime("%Y-%m-%d %H:%M:%S")


def get_assigned_channels(conn):
    """Get all channel_ids assigned to a field_sector."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT unnest(ubibot_channel_ids) AS channel_id
            FROM field_sectors
            WHERE ubibot_channel_ids IS NOT NULL
        """)
        return [r[0] for r in cur.fetchall()]


def get_channel_field_map(channel_id):
    """Fetch channel metadata to map field1-15 to sensor names."""
    url = "https://webapi.ubibot.com/channels"
    resp = requests.get(url, params={"account_key": ACCOUNT_KEY}, timeout=30)
    resp.raise_for_status()
    channels = resp.json().get("channels", [])
    for ch in channels:
        if int(ch["channel_id"]) == channel_id:
            mapping = {}
            for i in range(1, 16):
                name = ch.get(f"field{i}")
                if name:
                    mapping[f"field{i}"] = name
            return mapping
    return {}


def fetch_summary(channel_id):
    """Fetch hourly summary data for the gap period."""
    url = f"https://webapi.ubibot.com/channels/{channel_id}/summary"
    params = {
        "account_key": ACCOUNT_KEY,
        "results": 5000,
        "start": START_DATE,
        "end": END_DATE,
    }
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if data.get("result") != "success":
        print(f"  [WARN] channel {channel_id}: {data.get('errorCode')} - {data.get('desp')}")
        return []
    return data.get("feeds", [])


def parse_feeds(channel_id, feeds, field_map):
    """Convert raw API feeds into rows for ubi_channels_fields.

    Feed format: created_at has tz offset (e.g. -03:00), field data is a dict
    with avg/count/min/max directly on the feed (not nested under 'feeds' key).
    """
    rows = []
    for feed in feeds:
        raw_ts = feed.get("created_at")
        if not raw_ts:
            continue
        try:
            # Parse ISO timestamp with timezone offset (e.g. "2026-03-01T00:00:00-03:00")
            dt = datetime.fromisoformat(raw_ts)
            dt_santiago = dt.astimezone(SANTIAGO).replace(tzinfo=None)
        except (ValueError, TypeError):
            continue

        # One summary_id per (channel, timestamp) row
        summary_id = uuid.uuid4().hex

        for field_key, sensor_name in field_map.items():
            field_data = feed.get(field_key)
            if not field_data or not isinstance(field_data, dict):
                continue
            avg = field_data.get("avg")
            if avg is None:
                continue
            rows.append({
                "summary_id": summary_id,
                "channel_id": channel_id,
                "created_at": dt_santiago,
                "date": dt_santiago.date(),
                "hour": dt_santiago.time().replace(minute=0, second=0, microsecond=0),
                "name": sensor_name,
                "avg": float(avg),
                "count": int(field_data.get("count") or 0),
                "min": float(field_data.get("min") or 0),
                "max": float(field_data.get("max") or 0),
            })
    return rows


def upsert_fields(conn, rows):
    """Upsert rows into ubi_channels_fields."""
    if not rows:
        return 0
    sql = """
        INSERT INTO ubi_channels_fields
            (created_at, channel_id, name, avg, count, min, max, date, hour, summary_id)
        VALUES
            (%(created_at)s, %(channel_id)s, %(name)s, %(avg)s, %(count)s,
             %(min)s, %(max)s, %(date)s, %(hour)s, %(summary_id)s)
        ON CONFLICT (created_at, channel_id, name) DO UPDATE
            SET avg        = EXCLUDED.avg,
                count      = EXCLUDED.count,
                min        = EXCLUDED.min,
                max        = EXCLUDED.max,
                summary_id = EXCLUDED.summary_id
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, rows, page_size=500)
    conn.commit()
    return len(rows)


def upsert_summary(conn, rows):
    """Ensure ubi_channel_summary has a row for each unique (summary_id, channel_id, created_at)."""
    if not rows:
        return
    seen = {}
    for r in rows:
        key = (r["created_at"], r["channel_id"])
        if key not in seen:
            seen[key] = r["summary_id"]

    sql = """
        INSERT INTO ubi_channel_summary (id, channel_id, created_at, date, hour)
        VALUES (%(id)s, %(channel_id)s, %(created_at)s, %(date)s, %(hour)s)
        ON CONFLICT (id) DO NOTHING
    """
    summary_rows = [
        {"id": sid, "channel_id": ch, "created_at": ts,
         "date": ts.date(), "hour": ts.time().replace(minute=0, second=0, microsecond=0)}
        for (ts, ch), sid in seen.items()
    ]
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, summary_rows, page_size=500)
    conn.commit()


def main():
    conn = psycopg2.connect(DB_URL)

    print(f"Recovering Ubibot fields from {START_DATE} to {END_DATE}\n")

    channels = get_assigned_channels(conn)
    print(f"Channels assigned to field_sectors: {channels}\n")

    print("Fetching channel field map from API...")
    field_maps = {}
    for ch in channels:
        field_maps[ch] = get_channel_field_map(ch)
        print(f"  channel {ch}: {list(field_maps[ch].values())}")

    total_inserted = 0
    for i, channel_id in enumerate(channels):
        print(f"\n[{i+1}/{len(channels)}] channel {channel_id}...")
        try:
            feeds = fetch_summary(channel_id)
            print(f"  API returned {len(feeds)} hourly records")

            if not feeds:
                print("  No data — skipping")
                continue

            field_map = field_maps.get(channel_id, {})
            if not field_map:
                print("  No field map — skipping")
                continue

            rows = parse_feeds(channel_id, feeds, field_map)
            print(f"  Parsed {len(rows)} sensor readings")

            upsert_summary(conn, rows)
            inserted = upsert_fields(conn, rows)
            total_inserted += inserted
            print(f"  Upserted {inserted} rows into ubi_channels_fields")

        except Exception as e:
            print(f"  ERROR: {e}")
            conn.rollback()

        # Rate limiting — 6s between each request to stay under Ubibot's threshold
        time.sleep(6)

    conn.close()
    print(f"\nDone. Total rows upserted: {total_inserted}")


if __name__ == "__main__":
    main()
