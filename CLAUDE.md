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

## Naming Conventions

All database objects and code identifiers must be in **English**:
- Table names: `field_sectors`, `execution_log`, `wc_farms_zones`
- Column names: `irrigation_sector`, `crop_type`, `created_at`
- View names: use English (existing Spanish views `v_evapo_diario`, `v_kc_diario` are legacy)
- Function names, variable names, and Python identifiers: English only

Data values (farm names, orchard names, crop names) may remain in Spanish as they reflect real-world field names.

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

## Master Table: `field_sectors`

Single source of truth linking irrigation sectors across both data sources:

| Column | Description |
|--------|-------------|
| `id` | Primary key |
| `field` | Farm name (ZUÑIGA / ISLA DE MAIPO) |
| `farm_id` | Wiseconn farm ID — `14245` = Zuñiga, `60544` = Isla de Maipo |
| `irrigation_sector` | Sector name as it appears in Wiseconn (`wc_farms_zones.name`) |
| `wc_zone_id` | FK to `wc_farms_zones.id` — direct join to all Wiseconn data |
| `orchard` | Cuartel name (variety + year + CC code, e.g. `CEREZOS LAPINS 2014 CC-881`) |
| `crop_type` | `CEREZOS` or `CIRUELOS` |
| `ubibot_channel_ids` | `INTEGER[]` — array of Ubibot `channel_id`s monitoring this sector. Join with `ubi_channel_data` or `ubi_channel_summary` using `= ANY(ubibot_channel_ids)` |

Example joins:
```sql
-- Wiseconn sensor data for a sector
SELECT s.* FROM wc_zones_sensors s
JOIN field_sectors fs ON s.zone_id::float::int = fs.wc_zone_id
WHERE fs.orchard = 'CEREZOS LAPINS 2014 CC-881';

-- Ubibot readings for a sector
SELECT u.* FROM ubi_channel_summary u
JOIN field_sectors fs ON u.channel_id = ANY(fs.ubibot_channel_ids)
WHERE fs.irrigation_sector = 'Sector 2 EQ 2 (Lap14)';
```

**Pending mappings** (no Ubibot channel identified — confirm with field team):
- ZUÑIGA / Sector 3 EQ 3 (Lap19) / CEREZOS LAPINS 2019 CC-891
- ZUÑIGA / Sector 4 EQ 1 (Cer 24) / CEREZOS GLOW
- ISLA DE MAIPO / S1 EQ1 (Tul) / CIRUELAS TULARE CC-450
- ISLA DE MAIPO / S4 EQ2 / CIRUELAS TULARE CC-450

**Ubibot channels not yet assigned to any sector** (confirm with field team):
- `88158` T-Peonias, `88155` T-Peonias Sin Malla, `88251` T-Peonías Ensayo 3, `88259` T-Pimentónes Macro Tunel, `88271` T-Túnel Peonías Ensayo 1
- `89019` Z-IVU 115 2018, `71208` Z-Kiwi

## Database Functions

`f_kc(p_fecha_desde, p_fecha_hasta, p_field[], p_orchard[])` — Main reporting function. Returns daily Kc per orchard by joining `wc_farms_realirrigation` + `field_sectors` + `wc_zones_sensors` (Et0). Et0 is averaged across all EMAs per field. `p_field` and `p_orchard` are optional filters. Columns: `fecha`, `field`, `orchard`, `crop_type`, `irrigated_mm`, `et0_mm`, `kc`.

`f_ambient_temperature(p_fecha_desde, p_fecha_hasta, p_canales[])` — Hourly ambient temperature from Ubibot sensors. Excludes tunnel sensors (T-* prefix). Columns: `date`, `hour`, `channel`, `channel_id`, `temp_avg`, `temp_min`, `temp_max`.

## Production DB Access

Credentials live in GCP Secret Manager (never hardcode them). To connect with psql:

```bash
# Get DATABASE_URL from Secret Manager
DB_URL=$(gcloud secrets versions access latest --secret="DATABASE_URL" --project=integraciones-484915)

# Connect
psql "$DB_URL"
```

Cloud SQL instance: `db-donar` (PostgreSQL 16, `southamerica-west1`). GCP account: `gestion@empresasdonar.cl`.

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
