# Farm Irrigation Management System

Agricultural irrigation management system that integrates sensor data from Wiseconn and Ubibot.

## Table of Contents
1. [Installation](#installation)
2. [Environment Setup](#environment-setup)
3. [Development vs Production](#development-vs-production)
4. [Git-Crypt Setup](#git-crypt-setup)
5. [Usage](#usage)
6. [API Documentation](#api-documentation)
7. [Database Schema](#database-schema)
8. [Contributors](#contributors)

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
| `SENDGRID_API_KEY` | SendGrid API key for email alerts |

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
├── config.py                # Flask configuration
├── run.py                   # Main entry point
├── task_scheduler.py        # APScheduler for cron jobs
├── requirements.txt         # Python dependencies
├── .env                     # Production credentials (encrypted)
├── .env.local               # Local dev overrides (not in git)
├── .env.example             # Template for new devs
├── .gitattributes           # Git-crypt config
└── .gitignore               # Git ignore rules
```

---

## Contributors

- Bedomax
- Heimdallgg
- GestionD
