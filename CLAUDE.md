# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run main data sync (fetches Wiseconn + Ubibot, persists to DB)
python run.py

# Run daily channel alert report (email about downed sensors)
python daily_channel_report.py

# Run with local scheduler (hourly sync + daily alerts)
python task_scheduler.py

# DB migrations
flask db migrate -m "description"
flask db upgrade
```

## Environment & Safety

`.env.local` overrides `.env` for local dev. `app/environment.py` runs a safety check on import — it **blocks execution** if `ENV != production` and `DATABASE_URL` points to a remote host. To work locally, always set `DATABASE_URL` to localhost in `.env.local`.

Encrypted files (`.env`) require git-crypt: `git-crypt unlock /path/to/git-crypt-integraciones`

## Architecture

The system runs as a **Cloud Run Job** (project `integraciones-484915`, region `southamerica-west1`) triggered hourly by Cloud Scheduler. Push to `main` auto-deploys via GitHub Actions.

**Production DB**: Cloud SQL PostgreSQL 16 at `34.176.199.22:5432`, database `donar_prod`.

**Main execution flow** (`run.py`):
1. Two data sources fetched concurrently via `ThreadPoolExecutor(80 workers)`:
   - `run_fetch_process()` → Wiseconn API → zones, irrigation, sensors
   - `runubi_fetch_process()` → Ubibot API → channel summaries
2. Results persisted via `manage_data()` / `manage_data_ubi()`
3. Ubibot fields combined via `create_channel_sensor_mapping()` + `create_final_dataframe()`
4. Execution status logged to `execution_log` table
5. Alert email sent via Resend if any service fails

## Data Sources

**Wiseconn** (`api.wiseconn.com`) — irrigation management:
- Auth: `api_key` header
- Fetches: farms → zones → irrigations, realirrigations, measures → sensor data
- Key table: `wc_zones_sensors` stores all sensor readings including `Et0` and `Etc` (mm) for evapotranspiration

**Ubibot** (`webapi.ubibot.com`) — environmental IoT sensors:
- Auth: `account_key` query param
- Batched in groups of 10 with 60s sleep between batches (rate limiting)
- `field1`–`field15` on each channel map to sensor names (Temperature, Humidity, etc.)
- Summaries are hourly aggregates (avg/min/max/count)

## Key Architectural Decisions

- **Timezone**: All timestamps converted to `America/Santiago` then stored as naive (no tz info) to prevent PostgreSQL double-conversion
- **Deduplication**: Checks last 11 days before inserting; uses `(created_at, sensor_id, farm_id, zone_id)` as dedup key
- **Sensor data**: `wc_zones_sensors` stores only the **latest** value per sensor per run (not full time-series per sensor). For Et0/Etc, MAX per day = daily accumulated total
- **Logging**: Structured JSON logs via `log_processing_event()` helpers, compatible with Google Cloud Logging filters (`jsonPayload.service`, `jsonPayload.event_type`)

## Database Views

`v_evapo_diario` — pre-built view for evapotranspiration reporting (Looker Studio). Joins `wc_zones_sensors` + `wc_farms_zones`, returns `predio`, `sector`, `cultivo`, `sensor` (Et0/Etc), `fecha`, `valor_mm` (MAX per day).

## Active Farms

| farm_id | Predio |
|---------|--------|
| 14245 | Zuñiga |
| 60544 | Isla de Maipo |

## Deployment

```bash
# Manual job execution in GCP
gcloud run jobs execute integraciones-job --region=southamerica-west1 --project=integraciones-484915

# View logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=integraciones-job" \
  --project=integraciones-484915 --limit=50
```

Secrets are managed in GCP Secret Manager (project `integraciones-484915`) and injected at runtime. Local `.env` is encrypted with git-crypt.
