# Sistema de Integración de Riego — Empresas Donar

Sistema de gestión de riego agrícola que integra datos de sensores de Wiseconn y Ubibot para los predios **Zuñiga** e **Isla de Maipo**.

---

## ¿Eres usuario no técnico?

Si trabajas con reportes, análisis agronómicos o simplemente necesitas entender los datos disponibles, estos son los documentos pensados para ti:

| Documento | Para qué sirve |
|-----------|---------------|
| [**DATOS.md**](DATOS.md) | Qué significa cada tabla, columna y función. Con ejemplos SQL listos para usar |
| [**STATUS.md**](STATUS.md) | Calendario histórico del estado del sistema (sensores activos, riego, temperatura) — actualizado diariamente |
| [**SENSORS.md**](SENSORS.md) | Inventario completo de sensores por sector y cuartel |

---

## Índice (técnico)

1. [Instalación](#instalación)
2. [Variables de entorno](#variables-de-entorno)
3. [Desarrollo vs Producción](#desarrollo-vs-producción)
4. [Git-Crypt](#git-crypt)
5. [Despliegue en Google Cloud](#despliegue-en-google-cloud)
6. [Arquitectura y flujo de datos](#arquitectura-y-flujo-de-datos)
7. [Uso](#uso)
8. [Documentación de APIs](#documentación-de-apis)
9. [Schema de base de datos](#schema-de-base-de-datos)
10. [Integración AppSheet](#integración-appsheet)
11. [Contribuidores](#contribuidores)

---

## Instalación

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd Integraciones
```

### 2. Desencriptar archivos
Request the `git-crypt-integraciones` key file from a team member, then run:
```bash
git-crypt unlock /path/to/git-crypt-integraciones
```

### 3. Crear entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

### 4. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 5. Crear base de datos local (PostgreSQL)
```bash
createdb donar_dev
```

### 6. Ejecutar la aplicación
```bash
python run.py
```

---

## Variables de entorno

### Variables de entorno

| Variable | Description |
|----------|-------------|
| `ENV` | Environment: `production` or `development` |
| `API_KEY` | Wiseconn API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Flask secret key |
| `UBIBOT_ACCOUNT_KEY` | Ubibot API key |
| `RESEND_API_KEY` | Resend API key for email alerts |

### Archivos

| File | Purpose | Git Status |
|------|---------|------------|
| `.env` | Production credentials | Encrypted with git-crypt |
| `.env.local` | Local development overrides | Ignored (not in git) |
| `.env.example` | Template for new developers | Public |

### Ejemplo de `.env.local` para desarrollo:
```env
ENV=development
DATABASE_URL=postgresql://your_user@localhost/donar_dev
```

---

## Desarrollo vs Producción

La aplicación detecta el entorno automáticamente:

| Scenario | ENV | Database | Result |
|----------|-----|----------|--------|
| Local with `.env.local` | development | localhost | ✅ Runs |
| Production server | production | Remote DB | ✅ Runs |
| Local without `.env.local` | development | Remote DB | ❌ Blocked |

### Protección de base de datos
La aplicación incluye un bloqueo que impide conectarse accidentalmente a la base de datos de producción desde entorno de desarrollo:

```python
# app/environment.py
if ENV != 'production' and not is_local_database(DATABASE_URL):
    raise RuntimeError("SAFETY CHECK: Attempting to connect to remote database...")
```

---

## Git-Crypt

El archivo `.env` con credenciales de producción está encriptado con git-crypt.

### Para nuevos integrantes del equipo:
1. Solicitar el archivo `git-crypt-integraciones` a un miembro del equipo
2. Ejecutar: `git-crypt unlock /path/to/git-crypt-integraciones`

### Exportar la llave (para compartir):
```bash
git-crypt export-key git-crypt-integraciones
```

**Importante:** Nunca commitear el archivo de llave. Ya está en `.gitignore`.

---

## Despliegue en Google Cloud

La aplicación corre en **Google Cloud Run Jobs** con despliegue automático vía GitHub Actions.

### Arquitectura

| Component | Service | Region |
|-----------|---------|--------|
| Job Execution | Cloud Run Jobs | southamerica-west1 (Santiago) |
| Docker Images | Artifact Registry | southamerica-west1 |
| Secrets | Secret Manager | Global |
| Scheduler | Cloud Scheduler | southamerica-east1 (São Paulo) |
| Database | Cloud SQL PostgreSQL | southamerica-west1 |

### Despliegue automático (CI/CD)

Un push a la rama `main` dispara el despliegue automático:

```
Push to main → GitHub Actions → Build Docker → Push to Artifact Registry → Deploy to Cloud Run
```

The workflow is defined in `.github/workflows/deploy.yml`.

### Secrets de GitHub requeridos

Configurar en GitHub → Settings → Secrets and variables → Actions:

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | Google Cloud project ID (e.g., `integraciones-484915`) |
| `WIF_PROVIDER` | Workload Identity Federation provider URL |
| `WIF_SERVICE_ACCOUNT` | Service account email for GitHub Actions |

### Secrets de Google Cloud (Secret Manager)

Estos secrets se guardan en GCP Secret Manager y se inyectan en tiempo de ejecución:

| Secret | Description |
|--------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (URL-encoded) |
| `API_KEY` | Wiseconn API key |
| `SECRET_KEY` | Flask secret key |
| `UBIBOT_ACCOUNT_KEY` | Ubibot API key |
| `RESEND_API_KEY` | Resend API key |

### Ejecución programada

Cloud Scheduler ejecuta el job automáticamente:
- **Schedule**: Every hour at minute 0 (`0 * * * *`)
- **Timezone**: America/Santiago (Chile)

### Ejecución manual

```bash
# Execute job manually
gcloud run jobs execute integraciones-job-staging --region=southamerica-west1 --project=integraciones-484915

# View execution logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=integraciones-job-staging" --project=integraciones-484915 --limit=50
```

### Ver en consola GCP

- **Jobs**: https://console.cloud.google.com/run/jobs?project=integraciones-484915
- **Logs**: https://console.cloud.google.com/logs?project=integraciones-484915
- **Scheduler**: https://console.cloud.google.com/cloudscheduler?project=integraciones-484915

### Configuración inicial (proyectos nuevos)

Ver [SETUP_GCLOUD.md](SETUP_GCLOUD.md) para instrucciones detalladas de:
1. Enabling required APIs
2. Creating Artifact Registry
3. Setting up Secret Manager
4. Configuring Workload Identity Federation for GitHub Actions
5. Creating Cloud Scheduler

### Costo estimado mensual

| Service | Monthly Cost |
|---------|-------------|
| Cloud Run Jobs | ~$0-5 (pay per execution) |
| Artifact Registry | ~$0.10/GB |
| Secret Manager | ~$0.06/secret |
| Cloud Scheduler | Free (first 3 jobs) |
| **Total** | **~$1-5/month** |

---

## Arquitectura y flujo de datos

### Visión general

El sistema integra dos fuentes de datos para monitoreo agrícola:

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

### Integración Ubibot

**Qué es:** Sensores IoT que miden condiciones ambientales y de suelo (temperatura, humedad, luz, etc.)

#### Estructura de datos

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

#### Flujo de procesamiento

```
1. API Ubibot → clean_channel_data() → Lista de canales
2. API Ubibot → clean_channel_data_summary() → Resúmenes horarios
3. create_final_dataframe() → Combina canales + resúmenes → Tabla de campos final
```

#### Notas importantes

- **No todos los dispositivos tienen 15 sensores**: La mayoría tiene 3-4 (temperatura, humedad, etc.). El sistema busca los 15 campos posibles pero solo procesa los que existen.
- **Agregación horaria**: Los datos se agregan por hora con métricas avg, min, max y count.
- **Ventana de 11 días**: El sistema solo verifica registros existentes en los últimos 11 días para optimizar las queries.

---

### Integración Wiseconn

**Qué es:** Sistema de riego inteligente — controla y monitorea el riego en los campos agrícolas.

#### Estructura de datos

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

#### Flujo de procesamiento

```
1. API Wiseconn /zones → process_data_wc_farms_zones() → Sectores de riego
2. API Wiseconn /irrigation → process_data_irrigation() → Riego programado
3. API Wiseconn /realIrrigation → process_data_real_irrigation() → Riego ejecutado
4. API Wiseconn /measures → process_data_measures() → Sensores
```

---

### Logging (Google Cloud)

El sistema usa logging JSON estructurado compatible con Google Cloud Logging.

#### Formato de log

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

#### Tipos de evento

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

#### Filtros en Google Cloud Console

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

## Uso

### Ejecutar una vez (desarrollo)
```bash
source venv/bin/activate
python run.py
```

### Ejecutar con scheduler (producción local)
```bash
python task_scheduler.py
```

Tareas programadas:
- **Cada hora**: Descarga datos de Wiseconn y Ubibot
- **Diario a las 7:20 AM**: Envía alertas de sensores desconectados

---

## Documentación de APIs

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

## Schema de base de datos

> Para una descripción completa de cada tabla y columna, ver [DATOS.md](DATOS.md).

### Tablas Wiseconn

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

### Tablas Ubibot

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

### Tablas de sistema

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
├── daily_channel_report.py   # Daily Ubibot channel alert report
└── APPSHEET_INTEGRATION.md  # AppSheet integration plan
```

---

## Integración AppSheet

Migración de 40 apps AppSheet desde Google Sheets a PostgreSQL (Cloud SQL) como datasource directo.

**Ver documentación completa**: [APPSHEET_INTEGRATION.md](APPSHEET_INTEGRATION.md)

### Resumen

- **Objetivo**: Conectar apps AppSheet directamente a Cloud SQL PostgreSQL (lectura y escritura)
- **Arquitectura**: AppSheet → Cloud SQL PostgreSQL (conexión directa, sin intermediarios)
- **Apps**: 40 aplicaciones en 4 categorías (operaciones, maquinaria, control técnico, administración)
- **Estado**: Planificación

---

## Contribuidores

- Bedomax
- Heimdallgg
- GestionD
