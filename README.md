# Farm Irrigation Management System

Agricultural irrigation management system that integrates sensor data from Wiseconn and Ubibot.

## Table of Contents
1. [Installation](#installation)
2. [Environment Setup](#environment-setup)
3. [Development vs Production](#development-vs-production)
4. [Git-Crypt Setup](#git-crypt-setup)
5. [Google Cloud Deployment](#google-cloud-deployment)
6. [Data Flow & Architecture](#data-flow--architecture)
7. [Usage](#usage)
8. [API Documentation](#api-documentation)
9. [Database Schema](#database-schema)
10. [AppSheet Integration](#appsheet-integration)
11. [Contributors](#contributors)

---

## Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd Integraciones
```

### 2. Unlock encrypted files
Request the `git-crypt-integraciones` key file from a team member, then run:
```bash
git-crypt unlock /path/to/git-crypt-integraciones
```

### 3. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Setup local database (PostgreSQL)
```bash
createdb donar_dev
```

### 6. Run the application
```bash
python run.py
```

---

## Environment Setup

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ENV` | Environment: `production` or `development` |
| `API_KEY` | Wiseconn API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Flask secret key |
| `UBIBOT_ACCOUNT_KEY` | Ubibot API key |
| `RESEND_API_KEY` | Resend API key for email alerts |

### Files

| File | Purpose | Git Status |
|------|---------|------------|
| `.env` | Production credentials | Encrypted with git-crypt |
| `.env.local` | Local development overrides | Ignored (not in git) |
| `.env.example` | Template for new developers | Public |

### Example `.env.local` for development:
```env
ENV=development
DATABASE_URL=postgresql://your_user@localhost/donar_dev
```

---

## Development vs Production

The application automatically detects the environment:

| Scenario | ENV | Database | Result |
|----------|-----|----------|--------|
| Local with `.env.local` | development | localhost | ✅ Runs |
| Production server | production | Remote DB | ✅ Runs |
| Local without `.env.local` | development | Remote DB | ❌ Blocked |

### Safety Check
The application includes a safety check that prevents accidentally connecting to the production database from a development environment:

```python
# app/environment.py
if ENV != 'production' and not is_local_database(DATABASE_URL):
    raise RuntimeError("SAFETY CHECK: Attempting to connect to remote database...")
```

---

## Git-Crypt Setup

The `.env` file containing production credentials is encrypted with git-crypt.

### For new team members:
1. Get the `git-crypt-integraciones` key file from a team member
2. Run: `git-crypt unlock /path/to/git-crypt-integraciones`

### Export the key (for sharing with team):
```bash
git-crypt export-key git-crypt-integraciones
```

**Important:** Never commit the key file to git. It's already in `.gitignore`.

---

## Google Cloud Deployment

The application runs on **Google Cloud Run Jobs** with automatic deployment via GitHub Actions.

### Architecture

| Component | Service | Region |
|-----------|---------|--------|
| Job Execution | Cloud Run Jobs | southamerica-west1 (Santiago) |
| Docker Images | Artifact Registry | southamerica-west1 |
| Secrets | Secret Manager | Global |
| Scheduler | Cloud Scheduler | southamerica-east1 (São Paulo) |
| Database | Cloud SQL PostgreSQL | southamerica-west1 |

### Automatic Deployment (CI/CD)

Push to `main` branch triggers automatic deployment:

```
Push to main → GitHub Actions → Build Docker → Push to Artifact Registry → Deploy to Cloud Run
```

The workflow is defined in `.github/workflows/deploy.yml`.

### GitHub Secrets Required

Configure these in GitHub → Settings → Secrets and variables → Actions:

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | Google Cloud project ID (e.g., `integraciones-484915`) |
| `WIF_PROVIDER` | Workload Identity Federation provider URL |
| `WIF_SERVICE_ACCOUNT` | Service account email for GitHub Actions |

### Google Cloud Secrets (Secret Manager)

These secrets are stored in Google Cloud Secret Manager and injected at runtime:

| Secret | Description |
|--------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (URL-encoded) |
| `API_KEY` | Wiseconn API key |
| `SECRET_KEY` | Flask secret key |
| `UBIBOT_ACCOUNT_KEY` | Ubibot API key |
| `RESEND_API_KEY` | Resend API key |

### Scheduled Execution

Cloud Scheduler runs the job automatically:
- **Schedule**: Every hour at minute 0 (`0 * * * *`)
- **Timezone**: America/Santiago (Chile)

### Manual Execution

```bash
# Execute job manually
gcloud run jobs execute integraciones-job-staging --region=southamerica-west1 --project=integraciones-484915

# View execution logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=integraciones-job-staging" --project=integraciones-484915 --limit=50
```

### View in Console

- **Jobs**: https://console.cloud.google.com/run/jobs?project=integraciones-484915
- **Logs**: https://console.cloud.google.com/logs?project=integraciones-484915
- **Scheduler**: https://console.cloud.google.com/cloudscheduler?project=integraciones-484915

### Initial Setup (for new projects)

See [SETUP_GCLOUD.md](SETUP_GCLOUD.md) for detailed instructions on:
1. Enabling required APIs
2. Creating Artifact Registry
3. Setting up Secret Manager
4. Configuring Workload Identity Federation for GitHub Actions
5. Creating Cloud Scheduler

### Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| Cloud Run Jobs | ~$0-5 (pay per execution) |
| Artifact Registry | ~$0.10/GB |
| Secret Manager | ~$0.06/secret |
| Cloud Scheduler | Free (first 3 jobs) |
| **Total** | **~$1-5/month** |

---

## Data Flow & Architecture

### Overview

The system integrates two data sources for agricultural monitoring:

```
┌─────────────┐     ┌─────────────────────┐     ┌──────────────┐
│   UBIBOT    │     │    Integraciones    │     │   WISECONN   │
│  (Sensors)  │     │                     │     │  (Irrigation)│
└──────┬──────┘     │  ┌───────────────┐  │     └──────┬───────┘
       │            │  │   PostgreSQL  │  │            │
       ▼            │  │               │  │            ▼
  Temperature       │  │ ubi_channels  │  │       Zones
  Humidity     ────►│  │ ubi_summary   │◄───    Irrigation
  Light             │  │ ubi_fields    │  │     Sensors
                    │  │               │  │
                    │  │ wc_zones      │  │
                    │  │ wc_irrigation │  │
                    │  │ wc_measures   │  │
                    │  └───────────────┘  │
                    └─────────────────────┘
```

---

### Ubibot Integration

**What is it?** IoT sensors that measure environmental conditions (temperature, humidity, light, etc.)

#### Data Structure

```
Channels (ubi_channels)
├── channel_id: 88738 (unique device identifier)
├── name: "Sensor Bodega Norte"
├── latitude/longitude: location
└── field1-field15: installed sensor names
    ├── field1: "Temperature"
    ├── field2: "Humidity"
    ├── field3: "Light"
    └── field4-15: (empty if device has fewer sensors)

Hourly Summaries (ubi_channel_summary)
├── channel_id: 88738
├── created_at: "2026-02-04 09:00:00"
├── field1_avg: 22.5 (temperature average)
├── field1_min: 21.0
├── field1_max: 24.0
├── field1_count: 12 (readings per hour)
├── field2_avg: 65.3 (humidity average)
└── ... (metrics for each active field)

Final Fields (ubi_channels_fields)
├── channel_id: 88738
├── name: "Temperature"
├── avg: 22.5
├── min: 21.0
├── max: 24.0
└── count: 12
```

#### Processing Flow

```
1. API Ubibot → clean_channel_data() → Channel list
2. API Ubibot → clean_channel_data_summary() → Hourly summaries
3. create_final_dataframe() → Combines channels + summaries → Final fields table
```

#### Important Notes

- **Not all devices have 15 sensors**: Most devices only have 3-4 sensors (temperature, humidity, etc.). The system searches for all 15 possible fields but only processes those that exist.
- **Hourly aggregation**: Data is aggregated hourly with avg, min, max, and count metrics.
- **11-day window**: The system only checks for existing records within the last 11 days to optimize queries.

---

### Wiseconn Integration

**What is it?** Smart irrigation system - controls and monitors irrigation in agricultural fields.

#### Data Structure

```
Zones (wc_farms_zones)
├── id: irrigation zone
├── farm_id: farm
├── name: "Sector Norte - Paltos"
├── area_m2: 5000
├── theoreticalflow: theoretical flow rate
└── coordinates: polygon bounds

Scheduled Irrigation (wc_farms_irrigation)
├── zone_id: affected zone
├── farm_id: farm
├── inittime/endtime: scheduled time
├── volume_m3: volume to irrigate
├── precipitation_mm: precipitation
└── delta_time: duration

Real Irrigation (wc_farms_real_irrigation)
├── zone_id: zone
├── init_time/end_time: actual irrigation time
├── volume_m3: actual volume applied
├── flow_m3_h: actual flow rate
├── pressure: system pressure
└── scheduled_irrigation_id: reference to scheduled

Sensors/Measures (wc_zones_sensors)
├── sensor_id
├── name: "Soil Moisture", "Flow", "Pressure"
├── unit: "%", "m³/h", "bar"
└── zone_id: which zone it belongs to
```

#### Processing Flow

```
1. API Wiseconn /zones → process_data_wc_farms_zones() → Zones
2. API Wiseconn /irrigation → process_data_irrigation() → Scheduled irrigation
3. API Wiseconn /realIrrigation → process_data_real_irrigation() → Actual irrigation
4. API Wiseconn /measures → process_data_measures() → Sensors
```

---

### Logging (Google Cloud)

The system uses structured JSON logging for Google Cloud Logging.

#### Log Format

```json
{
  "service": "ubibot_sync",
  "event_type": "FIELDS_SYNC_SUCCESS",
  "message": "Campos sincronizados correctamente",
  "timestamp": "2026-02-04T09:04:04.123456",
  "data": {
    "registros_procesados": 1500,
    "canales_actualizados": 5,
    "tipos_campo": ["Temperature", "Humidity", "Light"]
  }
}
```

#### Event Types

| Service | Event Type | Description |
|---------|------------|-------------|
| `ubibot_sync` | `SYNC_START` | Synchronization started |
| `ubibot_sync` | `CHANNELS_SYNC_SUCCESS` | Channels synced successfully |
| `ubibot_sync` | `SUMMARY_SYNC_SUCCESS` | Summaries synced successfully |
| `ubibot_sync` | `FIELDS_SYNC_SUCCESS` | Fields synced successfully |
| `ubibot_sync` | `*_ERROR` | Error during sync |
| `data_processing` | `UBIBOT_CHANNELS_PROCESSED` | Channels processed |
| `data_processing` | `WISECONN_ZONES_PROCESSED` | Zones processed |
| `utils` | `FINAL_DATAFRAME_CREATED` | Final dataframe created |

#### Filtering in Google Cloud Console

```
# Filter by service
jsonPayload.service="ubibot_sync"

# Filter by event type
jsonPayload.event_type="FIELDS_SYNC_SUCCESS"

# Filter errors only
jsonPayload.event_type=~"ERROR"

# Filter by channel
jsonPayload.data.channel_id=88738
```

---

## Usage

### Run once (development)
```bash
source venv/bin/activate
python run.py
```

### Run with scheduler (production)
```bash
python task_scheduler.py
```

Scheduled tasks:
- **Hourly**: Fetch data from Wiseconn and Ubibot sensors
- **Daily at 7:20 AM**: Send alert emails for disconnected sensors

---

## API Documentation

### Wiseconn API

Base URL: `https://api.wiseconn.com`
Headers: `{'api_key': 'YOUR_API_KEY'}`

#### 1. FARMS
```
GET /farms
```
| Field | Type | Description |
|-------|------|-------------|
| id | int | Farm ID |
| name | str | Farm name |
| latitude | float | Latitude |
| longitude | float | Longitude |
| account.name | str | Account name |
| timeZone | str | Timezone (e.g., GMT-3) |

#### 2. ZONES
```
GET /farms/{farmId}/zones
```
| Field | Type | Description |
|-------|------|-------------|
| id | int | Zone ID |
| name | str | Zone name |
| farmId | int | Parent farm ID |
| type | [str] | Zone type (e.g., ['Irrigation']) |
| crops | str | Crop type |
| area | int | Area in m² |
| theoreticalFlow | int | Flow rate in m³/h |
| pumpSystemId | int | Pump system ID |
| irrigationScheduleStats | dict | {max, min, avg, std} |

#### 3. IRRIGATIONS (scheduled)
```
GET /farms/{farmId}/irrigations?initTime=YYYY-MM-DD&endTime=YYYY-MM-DD
```
| Field | Type | Description |
|-------|------|-------------|
| id | int | Irrigation ID |
| initTime | str | Start time (ISO 8601) |
| endTime | str | End time (ISO 8601) |
| status | str | Status (Executed OK, Pending, etc.) |
| zoneId | int | Zone ID |
| volume.value | float | Volume in m³ |
| precipitation.value | float | Precipitation in mm |

#### 4. REAL IRRIGATIONS (executed)
```
GET /farms/{farmId}/realIrrigations?initTime=YYYY-MM-DD&endTime=YYYY-MM-DD
```
| Field | Type | Description |
|-------|------|-------------|
| id | int | Real irrigation ID |
| initTime | str | Actual start time |
| endTime | str | Actual end time |
| status | str | Status (Executed OK, Executed with failure) |
| zoneId | int | Zone ID |
| volume.value | float | Actual volume in m³ |
| flow.value | float | Flow rate in m³/h |
| alarms | [dict] | Alarms triggered |
| measures | [dict] | Sensor measurements |

#### 5. MEASURES (sensors)
```
GET /farms/{farmId}/measures
```
| Field | Type | Description |
|-------|------|-------------|
| id | str | Sensor ID (e.g., 1-204761) |
| name | str | Sensor name |
| unit | str | Unit (e.g., m³/h) |
| sensorType | str | Type (Flow, Pressure, etc.) |
| lastData | float | Last reading |
| lastDataDate | str | Last reading timestamp |

#### 6. SENSOR DATA
```
GET /measures/{sensorId}/data?initTime=YYYY-MM-DD&endTime=YYYY-MM-DD
```
| Field | Type | Description |
|-------|------|-------------|
| time | str | Timestamp (ISO 8601) |
| value | float | Sensor value |

---

### Ubibot API

Base URL: `https://webapi.ubibot.com`
Params: `account_key=YOUR_KEY`

#### 1. CHANNELS
```
GET /channels?account_key=XXX
```
| Field | Type | Description |
|-------|------|-------------|
| channel_id | str | Channel ID |
| name | str | Device name |
| latitude | str | Latitude |
| longitude | str | Longitude |
| field1-field15 | str | Field names (Temperature, Humidity, etc.) |
| last_values | dict | Latest sensor readings |
| product_id | str | Device model |
| firmware | str | Firmware version |

#### 2. CHANNEL SUMMARY
```
GET /channels/{channelId}/summary?account_key=XXX&results=5000&start=YYYY-MM-DD&end=YYYY-MM-DD
```
| Field | Type | Description |
|-------|------|-------------|
| created_at | str | Timestamp |
| field1.avg | float | Average value |
| field1.min | float | Minimum value |
| field1.max | float | Maximum value |
| field1.count | int | Number of readings |
| field1.sum | float | Sum of values |

---

## Database Schema

### Wiseconn Tables

#### `wc_farms_zones`
| Column | Type | Description |
|--------|------|-------------|
| id | int | Zone ID (PK) |
| farm_id | int | Farm ID |
| name | text | Zone name |
| crops | text | Crop type |
| area_m2 | float | Area |
| irrigation_max/min/avg/std | float | Irrigation stats |

#### `wc_farms_irrigation`
| Column | Type | Description |
|--------|------|-------------|
| id | int | Irrigation ID (PK) |
| farm_id | int | Farm ID |
| zone_id | int | Zone ID |
| inittime | datetime | Start time |
| endtime | datetime | End time |
| status | text | Status |
| volume_m3 | float | Volume |

#### `wc_farms_realirrigation`
| Column | Type | Description |
|--------|------|-------------|
| id | int | Real irrigation ID (PK) |
| farm_id | int | Farm ID |
| zone_id | int | Zone ID |
| init_time | datetime | Actual start |
| end_time | datetime | Actual end |
| status | text | Status |
| volume_m3 | float | Actual volume |
| pressure | float | Pressure reading |

#### `wc_zones_sensors`
| Column | Type | Description |
|--------|------|-------------|
| sensor_id | str | Sensor ID (PK) |
| farm_id | str | Farm ID |
| zone_id | str | Zone ID |
| name | text | Sensor name |
| unit | text | Unit |
| values | float | Last value |

### Ubibot Tables

#### `ubi_channel_data`
| Column | Type | Description |
|--------|------|-------------|
| channel_id | int | Channel ID (unique) |
| name | str | Device name |
| latitude | str | Latitude |
| longitude | str | Longitude |

#### `ubi_channel_summary`
| Column | Type | Description |
|--------|------|-------------|
| id | str | Summary ID (PK) |
| channel_id | int | Channel ID |
| created_at | datetime | Timestamp |

#### `ubi_channels_fields`
| Column | Type | Description |
|--------|------|-------------|
| summary_id | str | Summary ID |
| channel_id | int | Channel ID |
| name | str | Field name |
| avg | float | Average |
| min | float | Minimum |
| max | float | Maximum |
| count | int | Count |

### System Tables

#### `execution_log`
| Column | Type | Description |
|--------|------|-------------|
| id | int | Log ID (PK) |
| status_wiseconn | str | Wiseconn status |
| status_ubibot | str | Ubibot status |
| date | datetime | Execution timestamp |

---

## Project Structure

```
Integraciones/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── environment.py       # Environment config & safety checks
│   ├── models.py            # SQLAlchemy models
│   └── services/
│       ├── wiseconn.py      # Wiseconn API client
│       ├── ubibot.py        # Ubibot API client
│       ├── database.py      # Wiseconn data persistence
│       ├── database_ubibot.py # Ubibot data persistence
│       ├── data_processing.py # Data transformation
│       └── utils.py         # Utility functions
├── .github/
│   └── workflows/
│       └── deploy.yml       # GitHub Actions CI/CD
├── config.py                # Flask configuration
├── run.py                   # Main entry point
├── task_scheduler.py        # APScheduler for cron jobs (local)
├── Dockerfile               # Container image for Cloud Run
├── .dockerignore            # Files excluded from Docker build
├── requirements.txt         # Python dependencies
├── .env                     # Production credentials (encrypted)
├── .env.local               # Local dev overrides (not in git)
├── .env.example             # Template for new devs
├── .gitattributes           # Git-crypt config
├── .gitignore               # Git ignore rules
├── SETUP_GCLOUD.md          # Google Cloud setup instructions
└── APPSHEET_INTEGRATION.md  # AppSheet integration plan
```

---

## AppSheet Integration

Planeación para integrar datos de aplicaciones AppSheet hacia PostgreSQL para habilitar reportes SQL.

**Ver documentación completa**: [APPSHEET_INTEGRATION.md](APPSHEET_INTEGRATION.md)

### Resumen

- **Objetivo**: Extraer datos de 40+ apps AppSheet y consolidarlos en PostgreSQL
- **Métodos**: AppSheet REST API (preferido) o Google Sheets API (fallback)
- **Arquitectura**: Cloud Run Job + Cloud Scheduler + Cloud SQL PostgreSQL
- **Estado**: Planificación

---

## Contributors

- Bedomax
- Heimdallgg
- GestionD
