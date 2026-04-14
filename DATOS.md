# Guía de Datos — Sistema de Integración Donar

Este documento explica qué datos recopila el sistema, de dónde vienen, cómo se organizan en la base de datos y qué significa cada tabla y columna. Está pensado para personas que trabajan con los reportes y necesitan entender la información disponible.

---

## Índice

- [¿Qué hace este sistema?](#qué-hace-este-sistema)
- [Los dos campos](#los-dos-campos)
- [Mapa de tablas](#mapa-de-tablas)
- [Tablas de referencia](#tablas-de-referencia)
  - [`field_sectors` — Tabla maestra de sectores](#field_sectors--tabla-maestra-de-sectores)
  - [`wc_farms_zones` — Sectores de riego Wiseconn](#wc_farms_zones--sectores-de-riego-wiseconn)
- [Tablas Wiseconn](#tablas-wiseconn)
  - [Cómo funciona la API de Wiseconn](#cómo-funciona-la-api-de-wiseconn)
  - [`wc_zones_sensors` — Lecturas de sensores](#wc_zones_sensors--lecturas-de-sensores)
  - [`wc_farms_realirrigation` — Riego real ejecutado](#wc_farms_realirrigation--riego-real-ejecutado)
  - [`wc_farms_irrigation` — Riego programado](#wc_farms_irrigation--riego-programado)
- [Tablas Ubibot](#tablas-ubibot)
  - [Cómo funciona la API de Ubibot](#cómo-funciona-la-api-de-ubibot)
  - [`ubi_channel_data` — Catálogo de dispositivos](#ubi_channel_data--catálogo-de-dispositivos-ubibot)
  - [`ubi_channel_summary` — Cabecera horaria](#ubi_channel_summary--cabecera-horaria-por-dispositivo)
  - [`ubi_channels_fields` — Lecturas por sensor](#ubi_channels_fields--lecturas-por-sensor)
- [Tabla de sistema](#tabla-de-sistema)
  - [`execution_log` — Historial de ejecuciones](#execution_log--historial-de-ejecuciones)
- [Tablas de reportería precalculadas](#tablas-de-reportería-precalculadas)
  - [`ubi_sensor_pivot` — Pivot de sensores por hora](#ubi_sensor_pivot--pivot-de-sensores-por-hora)
  - [`wc_kc_weekly` — Kc semanal por sector](#wc_kc_weekly--kc-semanal-por-sector)
  - [`ubi_ambient_temperature` — Temperatura ambiente horaria](#ubi_ambient_temperature--temperatura-ambiente-horaria)
  - [`ubi_soil_sensors` — Temperatura y humedad del suelo](#ubi_soil_sensors--temperatura-y-humedad-del-suelo-horaria)
  - [`ubi_chill_hours` — Horas frío por sector y temporada](#ubi_chill_hours--horas-frío-por-sector-y-temporada)
  - [`wc_ema` — Clima diario de la Estación Meteorológica Automática](#wc_ema--clima-diario-de-la-estación-meteorológica-automática)
    - [Modelo HF](#modelo-horas-frío-hf--el-más-simple)
    - [Modelo Utah](#modelo-utah-porciones-frío--intermedio)
    - [Grados Día (GDA)](#grados-día-acumulados-gda)
  - [`ubi_chill_portions` — Porciones frío Modelo Dinámico](#ubi_chill_portions--porciones-frío-modelo-dinámico)
    - [Modelo Dinámico](#modelo-dinámico-erez--fishman-1990)
- [Resumen de volumen de datos](#resumen-de-volumen-de-datos)
- [Sensores pendientes de confirmar](#sensores-pendientes-de-confirmar)

---

## ¿Qué hace este sistema?

Cada hora, el sistema se conecta automáticamente a **dos plataformas externas** y descarga todos los datos de sensores y riego de los dos campos de Empresas Donar. Esos datos se guardan en una base de datos central desde donde se generan los reportes.

```
Wiseconn (control de riego)  ──┐
                                ├──▶  Base de datos Donar  ──▶  Reportes
Ubibot (sensores ambientales) ──┘
```

Desde su puesta en marcha el sistema ha realizado más de **12.500 ejecuciones automáticas** y almacena datos desde junio 2024.

---

## Los dos campos

| Campo | Ubicación | farm_id |
|-------|-----------|---------|
| **Zuñiga** | Región del Libertador | 14245 |
| **Isla de Maipo** | Región Metropolitana | 60544 |

---

## Mapa de tablas

```
field_sectors  (tabla maestra — conecta todo)
     │
     ├── wc_zone_id ──────────▶ wc_farms_zones          (catálogo de sectores)
     │                               │
     │                               ├──▶ wc_zones_sensors        (lecturas de sensores, snapshot)
     │                               ├──▶ wc_farms_realirrigation  (riego real ejecutado)
     │                               └──▶ wc_farms_irrigation      (riego programado)
     │
     └── ubibot_channel_ids ──▶ ubi_channel_data         (catálogo de dispositivos)
                                      │
                                      ├──▶ ubi_channel_summary     (cabecera horaria por dispositivo)
                                      ├──▶ ubi_channels_fields     (lecturas por sensor)
                                      ├──▶ ubi_sensor_pivot        (pivot para reportes — 20 sensores como columnas)
                                      ├──▶ ubi_chill_hours         (HF, Utah, GDA — season desde 1/mayo)
                                      └──▶ ubi_chill_portions      (Modelo Dinámico — season desde 1/enero)

wc_ema         (clima diario EMA/Davis — temperatura, humedad, radiación, viento, lluvia)

execution_log  (registro de cada ejecución del sistema)
```

---

## Tablas de referencia

### `field_sectors` — Tabla maestra de sectores

**Propósito:** Fuente única de verdad que conecta cada sector de riego con sus datos de Wiseconn y sus sensores Ubibot. Tiene 22 filas — una por sector de riego.

**Registros:** 22

#### ¿Para qué sirve?

Es la tabla que **conecta todo el sistema**. Sin ella, no hay forma de saber qué sensor Ubibot monitorea qué cuartel, ni qué zona de Wiseconn corresponde a qué variedad. Siempre que se quiera responder una pregunta del tipo "¿qué pasó en el cuartel X?", el camino empieza por esta tabla.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Cómo |
|----------|------|
| **Ver todos los cuarteles y sus sectores** | Consulta directa — lista completa de los 22 sectores con campo, sector, cuartel y tipo de cultivo |
| **Punto de partida para cualquier join** | Todas las tablas de datos (Wiseconn y Ubibot) se unen a través de esta tabla usando `wc_zone_id` o `ubibot_channel_ids` |
| **Filtrar por predio o cultivo** | `WHERE field = 'ZUÑIGA'` o `WHERE crop_type = 'CEREZOS'` |
| **Ver qué sensores Ubibot cubren cada cuartel** | Columna `ubibot_channel_ids` — algunos cuarteles tienen más de un dispositivo |

```sql
-- Lista completa de cuarteles
SELECT field, irrigation_sector, orchard, crop_type, ubibot_channel_ids
FROM field_sectors
ORDER BY field, irrigation_sector;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `field` | text | Nombre del campo: `ZUÑIGA` o `ISLA DE MAIPO` |
| `farm_id` | integer | ID del **campo** en Wiseconn. `14245` = Zuñiga, `60544` = Isla de Maipo. Todos los sectores del mismo campo comparten este ID |
| `irrigation_sector` | text | Nombre del sector tal como aparece en Wiseconn (ej: `Sector 2 EQ 2 (Lap14)`) |
| `wc_zone_id` | integer | ID del **sector específico** dentro de Wiseconn. Único por sector. Se usa para hacer JOIN con `wc_farms_zones`, `wc_zones_sensors` y `wc_farms_realirrigation` |
| `orchard` | text | Nombre del cuartel con variedad, año y código (ej: `CEREZOS LAPINS 2014 CC-881`) |
| `crop_type` | text | Tipo de cultivo: `CEREZOS` o `CIRUELOS` |
| `ubibot_channel_ids` | integer[] | Array de IDs de los dispositivos Ubibot que monitorean este sector. Algunos sectores tienen más de uno. Se usa con `= ANY(ubibot_channel_ids)` |
| `created_at` | timestamp | Fecha de creación del registro |

> **`farm_id` vs `wc_zone_id`:** `farm_id` identifica el predio completo (todos los sectores de Zuñiga tienen `14245`). `wc_zone_id` identifica un sector específico dentro del predio — cada uno es único. Para unir datos de sensores o riego con un sector específico, siempre usar `wc_zone_id`.

---

### `wc_farms_zones` — Sectores de riego Wiseconn

**Propósito:** Catálogo de todos los sectores de riego. Se actualiza en cada ejecución con la última lectura de Wiseconn (sobreescribe el registro anterior).

**Registros:** 24 (22 sectores activos + 2 EMAs)

#### ¿Para qué sirve?

Es el catálogo técnico de cada sector de riego tal como lo conoce Wiseconn. Contiene la superficie, el caudal teórico del equipo y las coordenadas GPS de cada sector. Es la tabla que describe el **hardware** del sistema de riego — no los datos que genera, sino la configuración de cada zona.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Cómo |
|----------|------|
| **Ver superficie de cada cuartel** | `area_m2` — útil para calcular lámina de riego en mm/m² |
| **Conocer el caudal teórico de cada equipo** | `theoreticalflowm3h` — referencia para detectar si el caudal real difiere mucho del esperado |
| **Ver el Kc configurado en Wiseconn** | `kc` — comparar con el Kc calculado en `wc_kc_weekly` |
| **Obtener coordenadas para mapas** | `southwest_lat/lng`, `northeast_lat/lng` — bounding box de cada sector |
| **Ver estadísticas históricas de riego** | `irrigation_avg/max/min` — duración típica de los riegos por sector |

```sql
-- Superficie y caudal teórico por sector
SELECT z.name, fs.orchard, fs.field,
       z.area_m2, z.theoreticalflowm3h, z.kc
FROM wc_farms_zones z
JOIN field_sectors fs ON z.id = fs.wc_zone_id
ORDER BY fs.field, z.name;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | ID del sector en Wiseconn — mismo valor que `field_sectors.wc_zone_id` |
| `name` | text | Nombre del sector (ej: `Sector 2 EQ 2 (Lap14)`) |
| `farm_id` | integer | ID del campo al que pertenece |
| `area_m2` | double | Superficie del sector en m² |
| `theoreticalflowm3h` | double | Caudal teórico del equipo de riego en m³/h |
| `kc` | integer | Coeficiente de cultivo configurado en Wiseconn |
| `irrigation_avg` | double | Promedio histórico de duración de riegos (minutos) |
| `irrigation_max` | double | Máximo histórico de duración de riegos |
| `irrigation_min` | double | Mínimo histórico de duración de riegos |
| `southwest_lat/lng` | double | Coordenadas del borde suroeste del sector |
| `northeast_lat/lng` | double | Coordenadas del borde noreste del sector |
| `created_at` | timestamp | Fecha de la última actualización |

---

## Tablas Wiseconn

### Cómo funciona la API de Wiseconn

Wiseconn expone una jerarquía de 4 niveles que el pipeline recorre en cada ejecución:

```
/farms
  └── /farms/{id}/zones          (sectores de riego)
  └── /farms/{id}/measures       (catálogo de sensores por zona)
        └── /measures/{id}/data  (valores históricos del sensor)
  └── /farms/{id}/realIrrigations (eventos de riego ejecutados)
  └── /farms/{id}/irrigations     (programas de riego planificados)
```

**Autenticación:** header `api_key` en cada request.

#### Nivel 1 — `/farms`

Devuelve los dos predios. Se usan para generar dinámicamente los endpoints de zonas, medidas y riegos.

```json
{ "id": 14245, "name": "Zuñiga" }
{ "id": 60544, "name": "Isla de Maipo" }
```

#### Nivel 2 — `/farms/{id}/zones`

Devuelve los sectores de riego del predio. Zuñiga tiene 15 zonas, Isla de Maipo 9. Cada zona tiene un `id` que es el `zone_id` que atraviesa toda la base de datos.

```json
{ "id": 50918, "name": "Sector 1 EQ 1 (Dag)", "farmId": 14245, ... }
```

→ Se persiste en `wc_farms_zones`.

#### Nivel 3 — `/farms/{id}/measures`

Devuelve el catálogo completo de sensores del predio (~229 en Zuñiga). Cada sensor tiene un `id` único, el `zoneId` al que pertenece, el `name` del sensor, la unidad y el `lastData` (valor más reciente):

```json
{
  "id": "6-53361-1",
  "farmId": 14245,
  "zoneId": 53361,
  "name": "Et0",
  "unit": "mm",
  "lastData": 0.486,
  "lastDataDate": "2026-04-09T00:00:00.000Z",
  "sensorType": "Flow"
}
```

→ El pipeline toma el `lastData` de cada sensor y lo guarda en `wc_zones_sensors`.

#### Nivel 4 — `/measures/{id}/data?initTime=ayer&endTime=hoy`

Devuelve el historial de valores del sensor para el rango de fechas. El pipeline lo usa para sensores específicos (Et0, Etc) para asegurar que se capture el acumulado diario correcto:

```json
[
  { "time": "2026-04-08T00:00:00Z", "value": 3.094 },
  { "time": "2026-04-09T00:00:00Z", "value": 0.486 }
]
```

#### Por qué Et0 del día vale parcial hasta las 00:00

Et0 es un **acumulado diario** — Wiseconn va sumando la evapotranspiración hora a hora. A las 08:00 AM marca `0.486 mm`, pero seguirá creciendo hasta que a las 00:00 del día siguiente cierre el acumulado (ej: `3.094 mm` para el día completo anterior).

**Por eso `wc_kc_weekly` acumula con `SUM(MAX(Et0) por día)`** — el valor máximo del día equivale al acumulado final, y se suman los días de la semana para obtener el Et0 semanal. Consultar Et0 intradía dará siempre un valor menor al real.

#### Cómo entra a `wc_zones_sensors`

El pipeline toma el `lastData` de cada measure y hace upsert por `(date, sensor_id, zone_id)`:

```
sensor_id  = "6-53361-1"       ← id del measure en Wiseconn
name       = "Et0"
unit       = "mm"
values     = 0.486             ← lastData en el momento del run
date       = 2026-04-09        ← fecha actual
created_at = 2026-04-09 00:00:00
zone_id    = "53361.0"         ← zoneId del measure (con sufijo .0)
farm_id    = "14245"
```

La restricción unique `(date, sensor_id, zone_id)` significa que **cada ejecución horaria sobreescribe el valor del día**. No es una serie de tiempo por hora — es el snapshot más reciente del día.

#### Cómo entra a `wc_farms_realirrigation`

`/farms/{id}/realIrrigations?initTime=ayer&endTime=hoy` devuelve los eventos de riego ejecutados. Cada evento tiene inicio, fin, duración y volúmenes medidos. El pipeline los inserta directamente — un evento por fila, deduplicando por `id`.

---

### `wc_zones_sensors` — Lecturas de sensores

**Propósito:** Almacena el **último valor** de cada sensor en cada ejecución del pipeline. **No es una tabla de series de tiempo** — no guarda el historial completo de cada sensor, solo el snapshot más reciente cuando el pipeline corrió. Para Et0 y Etc, el valor del día es el acumulado diario (máximo del día).

**Registros:** ~317.000 | **Rango:** ago 2024 → hoy | **Frecuencia:** ~250 filas/día, ~57 tipos de sensor distintos

#### ¿Para qué sirve?

Es la tabla central de sensores de Wiseconn. Contiene datos de **dos tipos de fuente**:

- **EMAs (Estaciones Meteorológicas Automáticas):** miden condiciones climáticas del campo — temperatura, humedad, lluvia, viento, radiación solar, Et0.
- **Sensores de riego por sector:** miden lo que ocurre en cada equipo de riego — caudal, presión, volumen, fertigación, horas frío y grados día calculados por Wiseconn.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Sensores clave | Comentario |
|----------|---------------|------------|
| **Kc semanal por cuartel** | `Et0` + `wc_farms_realirrigation` | Base del reporte de Kc. La tabla `wc_kc_weekly` ya lo calcula semanalmente |
| **Evapotranspiración del cultivo** | `Etc` (mm) | 24 zonas, cubre todos los cuarteles activos |
| **Condiciones climáticas** | `Temperatura - EMA`, `Humedad Relativa - EMA`, `Pluviometría - EMA`, `Radiacion Solar - EMA`, `Velocidad Viento - EMA` | Una sola EMA por predio — sirve como referencia climática del campo |
| **Horas frío y grados día (Wiseconn)** | `Chill Hour Accumulated B7.2`, `Grados día Acumulado B10.0` | Calculado por Wiseconn directamente. Comparar con los modelos propios en `ubi_chill_hours` |
| **Caudales y presiones** | `Caudalimetro EQ1/2/3`, `FIP 1/2/3 EQ*`, `Presión Eq 1/2/3` | Detectar anomalías en los equipos de riego |
| **Fertigación** | `Fertigation Time`, `Fertigation Volume` | Cuánto fertilizante se aplicó por sector |
| **Alertas de equipos** | `Battery Level`, `RF Power`, `Corte de energia EQ1`, `Falla de Nivel EQ*` | Sensores de estado operacional — base para alertas |

#### Sensores disponibles

| Categoría | Sensores |
|-----------|----------|
| **Evapotranspiración** | `Et0` (mm), `Etc` (mm) |
| **Clima EMA** | `Temperatura - EMA`, `Humedad Relativa - EMA`, `Pluviometría - EMA`, `Radiacion Solar - EMA`, `Velocidad Viento - EMA`, `Rafaga de Viento - EMA`, `Dirección Viento - EMA`, `Presión Atmosférica - EMA` |
| **Clima Davis API** | `Temperatura Davis API`, `Humedad Relativa Davis API`, `Lluvia Davis API`, `Viento Davis API`, `Radiación Davis API`, `Presion Davis API` |
| **Riego** | `Irrigation Time` (min), `Irrigation Volume` (m³), `Irrigation Precipitation` (mm) |
| **Caudal** | `Caudalimetro EQ1/2/3`, `FIP 1/2/3 EQ1/2/3` (m³/h), `Volumen Acumulado - Caudalimetro EQ1/2` |
| **Presión** | `Presión Eq 1/2/3` (bar/Pa) |
| **Fertigación** | `Fertigation Time` (min), `Fertigation Volume` (l) |
| **Fenología** | `Chill Hour (Daily) B7.2`, `Chill Hour Accumulated B7.2` (h), `Hora frío Diario B7.2`, `Horas frío Acumulada B7.2`, `Grados Día Diario B10.0`, `Grados día Acumulado B10.0` (°C) |
| **Estado operacional** | `Battery Level` (%), `RF Power` (dB), `Current` (A), `Corte de energia EQ1`, `Falla de Nivel EQ1/2/3` |

**Registros:** ~317.000 | **Rango:** ago 2024 → hoy

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `sensor_id` | varchar | ID del sensor en Wiseconn (formato `"6-53361-1"`) |
| `name` | text | Nombre del sensor: `Et0`, `Etc`, `Temperatura - EMA`, `Caudalimetro EQ1`, etc. |
| `unit` | text | Unidad de medida: `mm`, `°C`, `%`, `m³/h`, `bar`, etc. |
| `values` | double | Valor de la lectura |
| `zone_id` | varchar | ID del sector. **Ojo:** se guarda con sufijo `.0` (ej: `"50927.0"`). Para hacer JOIN usar `CAST(NULLIF(zone_id,'NaN') AS numeric)::integer` |
| `farm_id` | varchar | ID del campo |
| `date` | date | Fecha de la lectura |
| `hour` | time | Hora de la lectura |
| `created_at` | timestamp | Timestamp exacto de la lectura |

**Ejemplo de uso:**
```sql
-- Et0 diario de Zuñiga (promedio de ambas EMAs)
SELECT date, AVG(values) AS et0
FROM wc_zones_sensors
WHERE name = 'Et0' AND farm_id = '14245'
GROUP BY date ORDER BY date DESC;

-- Sensores de un sector específico
SELECT s.name, s.values, s.unit, s.date
FROM wc_zones_sensors s
JOIN field_sectors fs ON CAST(NULLIF(s.zone_id,'NaN') AS numeric)::integer = fs.wc_zone_id
WHERE fs.orchard = 'CEREZOS LAPINS 2014 CC-881'
ORDER BY s.date DESC;

-- Horas frío acumuladas según Wiseconn (comparar con ubi_chill_hours)
SELECT date, zone_id, values AS horas_frio_acumuladas
FROM wc_zones_sensors
WHERE name = 'Chill Hour Accumulated B7.2'
ORDER BY date DESC, zone_id;

-- Alertas: sensores con batería baja
SELECT date, zone_id, farm_id, values AS bateria_pct
FROM wc_zones_sensors
WHERE name = 'Battery Level' AND values < 20
ORDER BY date DESC;
```

---

### `wc_farms_realirrigation` — Riego real ejecutado

**Propósito:** Registra cada evento de riego **realmente ejecutado** en el campo. Es la fuente de verdad para saber cuánto se regó, cuándo y en qué sector. Cada fila es un evento de riego completo con inicio, fin y volúmenes medidos.

**Registros:** ~6.700 | **Rango:** dic 2023 → hoy

#### ¿Para qué sirve?

Es la tabla más importante para el análisis de riego. Cada fila es un evento de riego que **realmente ocurrió** en el campo — con la duración exacta, los milímetros aplicados y el volumen medido. Es la base del cálculo de Kc y de cualquier análisis de eficiencia hídrica.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Columnas clave | Comentario |
|----------|---------------|------------|
| **Cuánto se regó por cuartel** | `precipitation_mm`, `zone_id` → JOIN `field_sectors` | La columna principal — mm de agua aplicados por evento |
| **Calendario de riegos** | `init_time`, `end_time`, `delta_time` | Ver cuándo y por cuánto tiempo se regó cada sector |
| **Volumen total de agua aplicada** | `volume_m3` | Para comparar con aforo o disponibilidad hídrica |
| **Eficiencia del equipo** | `flow_m3_h` vs `wc_farms_zones.theoreticalflowm3h` | Detectar caídas de caudal respecto al teórico |
| **Riegos con falla** | `status = 'Executed with failure'` | Identificar eventos donde algo salió mal |
| **Base del Kc** | `precipitation_mm` ÷ Et0 | Ya precalculado semanalmente en `wc_kc_weekly` |

```sql
-- Riego acumulado por cuartel en el último mes
SELECT fs.field, fs.orchard, 
       COUNT(*) AS eventos,
       SUM(r.precipitation_mm) AS mm_total,
       SUM(r.volume_m3) AS m3_total
FROM wc_farms_realirrigation r
JOIN field_sectors fs ON r.zone_id = fs.wc_zone_id
WHERE r.date >= CURRENT_DATE - 30
GROUP BY fs.field, fs.orchard
ORDER BY fs.field, mm_total DESC;

-- Riegos con falla recientes
SELECT r.init_time, r.end_time, fs.orchard, r.status, r.precipitation_mm
FROM wc_farms_realirrigation r
JOIN field_sectors fs ON r.zone_id = fs.wc_zone_id
WHERE r.status != 'Executed'
  AND r.date >= CURRENT_DATE - 14
ORDER BY r.init_time DESC;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `zone_id` | integer | ID del sector regado — JOIN con `field_sectors.wc_zone_id` |
| `farm_id` | integer | ID del campo |
| `init_time` | timestamp | Inicio del evento de riego |
| `end_time` | timestamp | Fin del evento de riego |
| `delta_time` | interval | Duración total del riego |
| `status` | text | Estado del riego: `Executed`, `Executed with failure`, etc. |
| `precipitation_mm` | double | **Milímetros de agua aplicados** — la columna principal para calcular Kc |
| `volume_m3` | double | Volumen total en m³ |
| `flow_m3_h` | double | Caudal promedio durante el riego en m³/h |
| `instantaneous_flow_m3_h` | double | Caudal instantáneo al inicio |
| `pressure` | double | Presión registrada durante el riego (bar) |
| `pump_system_id` | integer | Equipo de bombeo utilizado |
| `scheduled_irrigation_id` | double | ID del programa de riego que originó este evento |
| `measures` | jsonb | Datos adicionales de sensores durante el riego (JSON) |
| `date` | date | Fecha del evento (derivada de `init_time`) |
| `hour` | time | Hora del evento |

**Ejemplo de uso:**
```sql
-- Riego semanal por cuartel
SELECT fs.orchard, SUM(r.precipitation_mm) AS mm_regados
FROM wc_farms_realirrigation r
JOIN field_sectors fs ON r.zone_id = fs.wc_zone_id
WHERE r.date BETWEEN '2026-03-10' AND '2026-03-17'
GROUP BY fs.orchard ORDER BY mm_regados DESC;
```

---

### `wc_farms_irrigation` — Riego programado

**Propósito:** Registra los programas de riego **planificados**, no los ejecutados. Sirve para comparar lo programado versus lo real (`wc_farms_realirrigation`). Cada fila es un programa de riego con el riego teórico esperado.

**Registros:** ~6.200 | **Rango:** dic 2023 → hoy

#### ¿Para qué sirve?

Registra la **intención** del sistema de riego antes de que ocurra. Junto con `wc_farms_realirrigation`, permite responder preguntas como: ¿se regó lo que se programó? ¿Hubo programas cancelados? ¿Qué riegos están pendientes hoy?

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Columnas clave | Comentario |
|----------|---------------|------------|
| **Programado vs ejecutado** | JOIN con `wc_farms_realirrigation` vía `scheduled_irrigation_id` | Ver si el riego real coincide con el planificado |
| **Riegos pendientes o cancelados** | `status = 'Pending'` o `'Cancelled'` | Detectar sectores que no regaron según lo planeado |
| **Riegos manuales vs automáticos** | `irrigationtype` | Ver cuánta intervención manual hubo |
| **Planificación de agua** | `precipitation_mm`, `volume_m3` programados | Estimar cuánta agua se planificó aplicar |

```sql
-- Programas no ejecutados en los últimos 30 días
SELECT p.inittime, fs.orchard, p.status, p.irrigationtype,
       p.precipitation_mm AS mm_programados
FROM wc_farms_irrigation p
JOIN field_sectors fs ON p.zone_id = fs.wc_zone_id
WHERE p.status IN ('Cancelled', 'Pending')
  AND p.date >= CURRENT_DATE - 30
ORDER BY p.inittime DESC;

-- Comparar programado vs real por sector
SELECT fs.orchard,
       SUM(p.precipitation_mm) AS mm_programados,
       SUM(r.precipitation_mm) AS mm_reales,
       ROUND(SUM(r.precipitation_mm) / NULLIF(SUM(p.precipitation_mm), 0) * 100, 1) AS pct_ejecutado
FROM wc_farms_irrigation p
JOIN wc_farms_realirrigation r ON p.id = r.scheduled_irrigation_id
JOIN field_sectors fs ON p.zone_id = fs.wc_zone_id
WHERE p.date >= CURRENT_DATE - 30
GROUP BY fs.orchard ORDER BY pct_ejecutado;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `zone_id` | integer | ID del sector — JOIN con `field_sectors.wc_zone_id` |
| `farm_id` | integer | ID del campo |
| `inittime` | timestamp | Inicio programado del riego |
| `endtime` | timestamp | Fin programado del riego |
| `delta_time` | interval | Duración programada |
| `status` | text | Estado: `Executed`, `Pending`, `Cancelled`, etc. |
| `irrigationtype` | text | Tipo: `Automatic`, `Manual` |
| `scheduledtype` | text | Subtipo de programación |
| `precipitation_mm` | double | Milímetros de agua programados |
| `volume_m3` | double | Volumen programado en m³ |
| `theoreticalflow_m3_h` | double | Caudal teórico calculado |
| `pumpsystemid` | integer | Equipo de bombeo asignado |
| `senttonetwork` | boolean | Si el programa fue enviado al controlador |
| `groupingname` | text | Nombre del grupo de riego si aplica |
| `date` | date | Fecha del programa |
| `hour` | time | Hora del programa |

---

## Tablas Ubibot

### Cómo funciona la API de Ubibot

Ubibot expone dos endpoints principales que el pipeline usa en cada ejecución:

```
/channels                        (catálogo de todos los dispositivos)
/channels/{id}/summary           (resumen horario histórico por dispositivo)
```

**Autenticación:** query param `account_key` en cada request.

#### Endpoint 1 — `/channels`

Devuelve los 25 canales registrados en la cuenta. Para cada canal incluye el mapa de `field1`–`field15` → nombre del sensor instalado:

```json
{
  "channel_id": 88736,
  "name": "Sector 2 EQ2 (Lap14) (respaldo 2)",
  "field1": "Temperature",
  "field2": "Humidity",
  "field3": "Voltage",
  "field5": "GSM RSSI",
  "field6": "Light",
  "field7": "Temperatura del suelo (25 cm)",
  ...
}
```

Este mapa es esencial — sin él los valores de `field1`–`field15` en los feeds son números sin nombre. El pipeline lo usa para traducir campos a nombres al guardar en `ubi_channels_fields`.

→ Se persiste en `ubi_channel_data`.

#### Endpoint 2 — `/channels/{id}/summary`

Devuelve el historial de resúmenes horarios del dispositivo (hasta ~30 días). Cada `feed` es una hora:

```json
{
  "feeds": [
    {
      "created_at": "2026-04-09T07:00:00-03:00",
      "field1": { "sum": 22.19, "avg": 7.40, "count": 3, "sd": 0.04, "min": 7.36, "max": 7.44 },
      "field2": { "sum": 300.0, "avg": 100.0, "count": 3, "min": 100, "max": 100 },
      "field3": { "avg": 4.12, "count": 1, "min": 4.12, "max": 4.12 },
      "field5": { "avg": -69, "count": 1, "min": -71, "max": -63 },
      "field6": { "avg": 186.15, "count": 3, "min": 84.75, "max": 297.15 }
    }
  ]
}
```

**`count`** es el número de mediciones internas del sensor en esa hora — varía por tipo:
- `Temperature`, `Humidity`: count=12 (mide cada 5 min)
- `Voltage`, `GSM RSSI`: count=1 (mide una vez por hora por diseño)
- `Light`: count≈12 (puede ser menor en horas oscuras)

Un `count=0` con `avg=0` significa que el sensor físico no reportó esa hora — no es un error del pipeline.

#### Cómo entra a la base de datos (3 pasos)

**Paso 1 → `ubi_channel_summary`** (cabecera, 1 fila por canal por hora):
```
channel_id = 88736
date       = 2026-04-09
hour       = 07:00:00
```

**Paso 2 → `ubi_channels_fields`** (formato largo, N filas por canal por hora — una por sensor):
```
(88736, 'Temperature', avg=7.40, count=3, min=7.36, max=7.44, summary_id=...)
(88736, 'Humidity',    avg=100,  count=3, min=100,  max=100,  summary_id=...)
(88736, 'Voltage',     avg=4.12, count=1, min=4.12, max=4.12, summary_id=...)
(88736, 'GSM RSSI',    avg=-69,  count=1, min=-69,  max=-63,  summary_id=...)
(88736, 'Light',       avg=186,  count=3, min=84.75,max=297,  summary_id=...)
```

Deduplicación: `ON CONFLICT (created_at, channel_id, name) DO NOTHING` — si el registro ya existe, se ignora.

**Paso 3 → `ubi_sensor_pivot`** (formato ancho — `refresh_ubi_sensor_pivot()` al final del pipeline):
```
channel_id=88736 | orchard='CEREZOS LAPINS 2014 CC-881' | date=2026-04-09 | hour=07:00
temperature=7.40 | humidity=100 | light=186.15 | gsm_rssi=-69 | voltage=4.12
```

Aquí se incorporan los datos de `field_sectors` (campo, sector, cuartel) para evitar joins en los reportes.

#### Batching y rate limiting

Ubibot tiene rate limiting. El pipeline procesa los 25 canales en grupos de 10 con un sleep de 60 segundos entre grupos — por eso la parte de Ubibot tarda ~2-3 minutos del total de ~5 minutos de ejecución.

---

### `ubi_channel_data` — Catálogo de dispositivos Ubibot

**Propósito:** Catálogo con un registro por dispositivo Ubibot. Se sobreescribe en cada ejecución con los datos actuales del dispositivo.

**Registros:** 25

#### ¿Para qué sirve?

Es el directorio de los 25 dispositivos Ubibot instalados en ambos campos. Contiene el nombre, ubicación GPS y tipo de conexión de cada uno. Se usa principalmente para enriquecer consultas con el nombre legible del dispositivo o para saber su ubicación física.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Cómo |
|----------|------|
| **Ver todos los dispositivos instalados** | Consulta directa — lista de los 25 dispositivos con nombre y coordenadas |
| **Obtener el nombre del dispositivo en reportes** | JOIN con `channel_id` en cualquier tabla Ubibot |
| **Ver coordenadas GPS para mapas** | `latitude`, `longitude` — ubicación exacta de cada sensor en campo |
| **Verificar tipo de conexión** | `net` — si usa WiFi o GSM (útil para diagnosticar pérdida de señal) |

```sql
-- Lista de todos los dispositivos con sus coordenadas
SELECT channel_id, name, latitude, longitude, net
FROM ubi_channel_data
ORDER BY name;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria interna |
| `channel_id` | integer | ID del dispositivo en Ubibot — **clave de unión** con todas las tablas Ubibot |
| `name` | varchar | Nombre del dispositivo (ej: `Z-Santina 2014`, `I-1.2 Glow`) |
| `latitude` | varchar | Latitud GPS del dispositivo |
| `longitude` | varchar | Longitud GPS del dispositivo |
| `net` | integer | Tipo de conexión: WiFi o GSM |
| `date` | date | Fecha de la última actualización |
| `hour` | time | Hora de la última actualización |
| `created_at` | timestamp | Timestamp de la última actualización |

---

### `ubi_channel_summary` — Cabecera horaria por dispositivo

**Propósito:** Tabla de cabecera con un registro por dispositivo por hora. Sirve como índice de qué dispositivos reportaron datos en cada período. Cada fila está vinculada a múltiples lecturas en `ubi_channels_fields` a través de `summary_id`.

**Registros:** ~280.000 | **Rango:** may 2024 → hoy

#### ¿Para qué sirve?

Es la tabla "índice" de Ubibot — registra que un dispositivo reportó datos en una hora determinada, pero no los valores de los sensores en sí (esos están en `ubi_channels_fields`). Sirve principalmente como punto de join y para detectar brechas de conectividad: si un dispositivo no tiene fila en una hora, no reportó nada esa hora.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Cómo |
|----------|------|
| **Detectar dispositivos sin reporte** | Si un `channel_id` no tiene filas para una hora, el dispositivo estuvo offline |
| **Ver frecuencia de reporte por dispositivo** | `COUNT(*) GROUP BY channel_id, date` — cuántas horas reportó cada sensor |
| **Punto de JOIN para lecturas detalladas** | `ubi_channel_summary.id = ubi_channels_fields.summary_id` |

> **En la práctica**, la mayoría de consultas van directo a `ubi_channels_fields` o a las tablas precalculadas (`ubi_sensor_pivot`, `ubi_ambient_temperature`, etc.) sin pasar por esta tabla.

```sql
-- Dispositivos sin reporte en las últimas 24 horas
SELECT c.name, c.channel_id, MAX(s.created_at) AS ultimo_reporte
FROM ubi_channel_data c
LEFT JOIN ubi_channel_summary s ON c.channel_id = s.channel_id
GROUP BY c.name, c.channel_id
HAVING MAX(s.created_at) < NOW() - INTERVAL '24 hours' OR MAX(s.created_at) IS NULL
ORDER BY ultimo_reporte ASC;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | varchar(36) | UUID que identifica este resumen — se usa como `summary_id` en `ubi_channels_fields` |
| `channel_id` | integer | ID del dispositivo Ubibot |
| `created_at` | timestamp | Timestamp del resumen (hora exacta, sin timezone, hora de Chile) |
| `date` | date | Fecha del resumen |
| `hour` | time | Hora del resumen (ej: `14:00:00`) |

> Relación: 1 fila en `ubi_channel_summary` → N filas en `ubi_channels_fields` (una por cada sensor activo en ese dispositivo esa hora).

---

### `ubi_channels_fields` — Lecturas por sensor

**Propósito:** La tabla más importante de Ubibot. Contiene el valor de **cada sensor individual** de cada dispositivo, por hora, con estadísticas del período (promedio, mínimo, máximo y cantidad de lecturas). Es la fuente para todos los análisis de temperatura de suelo, humedad, CO₂, etc.

**Registros:** ~2.530.000 | **Rango:** may 2024 → hoy

#### ¿Para qué sirve?

Es el repositorio de **todas las lecturas brutas de Ubibot**. Cada dispositivo tiene múltiples sensores físicos instalados (temperatura, humedad, suelo, CO₂, etc.) y esta tabla guarda el promedio, mínimo y máximo de cada uno por hora. Es la fuente de datos más granular y completa de Ubibot — las tablas precalculadas (`ubi_sensor_pivot`, `ubi_ambient_temperature`, etc.) se construyen a partir de aquí.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Sensores clave | Comentario |
|----------|---------------|------------|
| **Temperatura ambiente por cuartel** | `Temperature` | Temperatura del aire. Para análisis de largo plazo, preferir `ubi_ambient_temperature` |
| **Humedad del suelo** | `Humedad del suelo (25 cm)`, `Humedad del suelo (50 cm)` | Disponibilidad hídrica en el perfil del suelo |
| **Temperatura del suelo** | `Temperatura del suelo (25 cm)`, `Temperatura del suelo (50 cm)` | Condición radicular y fenológica |
| **CO₂ en ambientes controlados** | `Carbon Dioxide` | Para túneles o estructuras cerradas |
| **Estado del dispositivo** | `Voltage` | Voltaje de la batería — bajo 3.6V empieza a fallar |
| **Lecturas de suelo vía RS485** | `RS485 Soil Moisture`, `RS485 Soil Temperature` | Sensores externos conectados al dispositivo Ubibot |
| **Variabilidad horaria** | `min` y `max` | Ver cuánto varió la temperatura dentro de cada hora |

> **Tip:** Para la mayoría de consultas de temperatura ambiente o suelo por cuartel, es más conveniente usar `ubi_sensor_pivot` (formato ancho, ya con nombres de cuartel) o `ubi_soil_sensors` (suelo específicamente). Esta tabla es útil cuando se necesita acceder a un sensor no incluido en las tablas precalculadas.

```sql
-- Ver todos los tipos de sensores disponibles por dispositivo
SELECT c.name AS dispositivo, f.name AS sensor, COUNT(*) AS horas_con_datos
FROM ubi_channels_fields f
JOIN ubi_channel_data c ON f.channel_id = c.channel_id
WHERE f.date >= CURRENT_DATE - 30
GROUP BY c.name, f.name
ORDER BY c.name, f.name;

-- Temperatura mínima nocturna por cuartel (últimos 7 días)
SELECT f.date, fs.orchard, MIN(f.min) AS temp_min_noche
FROM ubi_channels_fields f
JOIN field_sectors fs ON f.channel_id = ANY(fs.ubibot_channel_ids)
WHERE f.name = 'Temperature'
  AND f.hour BETWEEN '22:00' AND '06:00'
  AND f.date >= CURRENT_DATE - 7
GROUP BY f.date, fs.orchard
ORDER BY f.date DESC, temp_min_noche;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `summary_id` | varchar(36) | Referencia a `ubi_channel_summary.id` — agrupa todos los sensores del mismo dispositivo en la misma hora |
| `channel_id` | integer | ID del dispositivo Ubibot |
| `name` | varchar | Nombre del sensor: `Temperature`, `Humidity`, `Temperatura del suelo (25 cm)`, `Humedad del suelo (50 cm)`, `Carbon Dioxide`, `Voltage`, etc. |
| `avg` | double | Promedio del sensor durante la hora |
| `min` | double | Valor mínimo registrado en la hora |
| `max` | double | Valor máximo registrado en la hora |
| `count` | integer | Número de lecturas que generaron el promedio (normalmente entre 1 y 12) |
| `date` | date | Fecha de la lectura |
| `hour` | time | Hora de la lectura |
| `created_at` | timestamp | Timestamp exacto (sin timezone, hora de Chile) |

**Restricción única:** `(created_at, channel_id, name)` — no puede haber dos lecturas del mismo sensor en el mismo dispositivo en el mismo momento.

**Ejemplo de uso:**
```sql
-- Temperatura y humedad del suelo de un sector en la última semana
SELECT f.date, f.hour, c.name AS dispositivo, f.name AS sensor, f.avg, f.min, f.max
FROM ubi_channels_fields f
JOIN ubi_channel_data c ON f.channel_id = c.channel_id
JOIN field_sectors fs ON f.channel_id = ANY(fs.ubibot_channel_ids)
WHERE fs.orchard = 'CEREZOS LAPINS 2014 CC-881'
  AND f.name IN ('Temperature', 'Humedad del suelo (25 cm)')
  AND f.date >= CURRENT_DATE - 7
ORDER BY f.date, f.hour, f.name;
```

---

## Tabla de sistema

### `execution_log` — Historial de ejecuciones

**Propósito:** Registra el resultado de cada ejecución automática del pipeline. Una fila por ejecución (una por hora normalmente). Es la base del calendario de estado en STATUS.md.

**Registros:** ~12.500 | **Rango:** jun 2024 → hoy

#### ¿Para qué sirve?

Es el registro de salud del sistema. Permite saber si el pipeline está funcionando correctamente, con qué frecuencia falla cada fuente de datos, y si hay brechas en la recolección. Si los datos de un sensor parecen incompletos, la primera pregunta es: ¿el pipeline corrió correctamente esa hora?

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Cómo |
|----------|------|
| **Ver si el sistema está funcionando** | Verificar las últimas filas — ¿hay un registro de hace menos de 1 hora? |
| **Tasa de éxito por fuente** | `SUM(CASE WHEN status_wiseconn = 'Success')` agrupado por semana |
| **Detectar períodos con datos faltantes** | Buscar horas sin fila en `execution_log` o con `status != 'Success'` |
| **Correlacionar fallas con datos incompletos** | Si hay un `Failed` en una hora, los datos de esa hora pueden estar incompletos |

```sql
-- Estado de las últimas 24 horas
SELECT date AT TIME ZONE 'America/Santiago' AS hora_local,
       status_wiseconn, status_ubibot
FROM execution_log
WHERE date >= NOW() - INTERVAL '24 hours'
ORDER BY date DESC;

-- Resumen de fallas por semana
SELECT DATE_TRUNC('week', date) AS semana,
       COUNT(*) AS ejecuciones,
       SUM(CASE WHEN status_wiseconn = 'Success' THEN 1 ELSE 0 END) AS wc_ok,
       SUM(CASE WHEN status_ubibot = 'Success' THEN 1 ELSE 0 END) AS ubi_ok
FROM execution_log
WHERE date >= NOW() - INTERVAL '60 days'
GROUP BY semana ORDER BY semana DESC;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `date` | timestamptz | Fecha y hora de la ejecución (UTC) |
| `status_wiseconn` | varchar(50) | Resultado de la conexión con Wiseconn: `Success` o `Failed: <motivo>` |
| `status_ubibot` | varchar(50) | Resultado de la conexión con Ubibot: `Success` o `Failed: <motivo>` |

**Ejemplo de uso:**
```sql
-- Tasa de éxito por semana
SELECT DATE_TRUNC('week', date) AS semana,
       COUNT(*) AS ejecuciones,
       SUM(CASE WHEN status_wiseconn = 'Success' THEN 1 ELSE 0 END) AS wc_ok,
       SUM(CASE WHEN status_ubibot = 'Success' THEN 1 ELSE 0 END) AS ubi_ok
FROM execution_log
WHERE date >= NOW() - INTERVAL '60 days'
GROUP BY semana ORDER BY semana DESC;
```

---

## Tablas de reportería precalculadas

Todas estas tablas siguen el mismo patrón:
- Se actualizan automáticamente al final de cada sync exitoso mediante funciones `refresh_*()`.
- Procesan solo los **últimos 2 días** con upsert (`ON CONFLICT DO UPDATE`).
- Incluyen `field_sector_id` (FK a `field_sectors.id`) para facilitar joins directos sin pasar por arrays.
- El backfill histórico cubre desde el origen de los datos disponibles.

---

### `ubi_sensor_pivot` — Pivot de sensores por hora

**Propósito:** Tabla precalculada orientada a reportes. Transforma `ubi_channels_fields` de formato largo (una fila por sensor) a formato ancho (una fila por dispositivo por hora, con cada sensor como columna). Incluye directamente los datos de `field_sectors` (campo, sector, cuartel) para evitar joins adicionales al consultar.

Se actualiza automáticamente al final de cada ejecución del pipeline mediante la función `refresh_ubi_sensor_pivot()`, que procesa solo los últimos 2 días con upsert.

**Registros:** ~213.000 | **Rango:** may 2024 → hoy | **Canales activos:** 10 de 18 | **Validado:** 2026-04-08

#### ¿Para qué sirve?

Es la tabla **más cómoda para reportes y dashboards de Ubibot**. En lugar de tener que filtrar por nombre de sensor y hacer pivots manualmente, aquí cada sensor es una columna — temperatura, humedad de suelo, CO₂ y más están en la misma fila. Además ya tiene el nombre del cuartel incorporado, eliminando el JOIN con `field_sectors`.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Columnas clave |
|----------|---------------|
| **Temperatura y humedad del aire por cuartel** | `temperature`, `humidity` |
| **Humedad del suelo a distintas profundidades** | `humedad_suelo_25cm`, `humedad_suelo_50cm`, `rs485_soil_moisture` |
| **Temperatura del suelo** | `temperatura_suelo_25cm`, `temperatura_suelo_50cm` |
| **Estado del dispositivo** | `voltage`, `gsm_rssi`, `wifi_rssi` — detectar batería baja o mala señal |
| **CO₂ en túneles o estructuras** | `carbon_dioxide`, `carbon_dioxide_c1` |
| **Reportes completos sin joins** | Una sola tabla con campo, sector, cuartel y todos los sensores |

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `channel_id` | integer | ID del dispositivo Ubibot |
| `field` | varchar | Campo: `ZUÑIGA` o `ISLA DE MAIPO` |
| `irrigation_sector` | varchar | Nombre del sector de riego |
| `orchard` | varchar | Nombre del cuartel |
| `crop_type` | varchar | `CEREZOS` o `CIRUELOS` |
| `date` | date | Fecha de la lectura |
| `hour` | time | Hora de la lectura |
| `voltage` | numeric | Voltaje del dispositivo (V) |
| `light` | numeric | Luz (lux) |
| `humidity` | numeric | Humedad ambiente (%) |
| `temperature` | numeric | Temperatura ambiente (°C) |
| `gsm_rssi` | numeric | Señal GSM (dBm) |
| `wifi_rssi` | numeric | Señal WiFi (dBm) |
| `temperatura_suelo_25cm` | numeric | Temperatura del suelo a 25 cm (°C) |
| `temperatura_suelo_50cm` | numeric | Temperatura del suelo a 50 cm (°C) |
| `humedad_suelo_25cm` | numeric | Humedad del suelo a 25 cm (%) |
| `humedad_suelo_50cm` | numeric | Humedad del suelo a 50 cm (%) |
| `rs485_soil_moisture` | numeric | Humedad de suelo vía RS485 (%) |
| `rs485_soil_temperature` | numeric | Temperatura de suelo vía RS485 (°C) |
| `rs485_humidity` | numeric | Humedad ambiente vía RS485 (%) |
| `rs485_temperature` | numeric | Temperatura ambiente vía RS485 (°C) |
| `carbon_dioxide` | numeric | CO₂ (ppm) |
| `external_light` | numeric | Luz exterior vía sensor externo (lux) |
| `pt100_temperature` | numeric | Temperatura vía sonda PT100 (°C) |
| `rs485_atmospheric_pressure` | numeric | Presión atmosférica vía RS485 (hPa) |
| `wind_speed` | numeric | Velocidad del viento (m/s) |
| `carbon_dioxide_c1` | numeric | CO₂ canal 1 (ppm) |

#### Calidad de datos (validado 2026-04-08)

| Columna | Completitud (últimos 7 días) | Nota |
|---------|------------------------------|------|
| `temperature` | 100% | Todos los canales activos |
| `humidity` | 100% | Todos los canales activos |
| `temperatura_suelo_25cm` | 100% | Todos los canales con sensor de suelo |
| `temperatura_suelo_50cm` | 100% | Todos los canales con sensor de suelo |
| `humedad_suelo_25cm` | 90.7% | Algunos canales no tienen este sensor |
| `humedad_suelo_50cm` | 100% | Todos los canales con sensor de suelo |
| `wind_speed` | 0% | Ningún canal tiene anemómetro instalado |

#### Estado de canales (validado 2026-04-08)

| channel_id | Cuartel | Última fecha | Estado |
|------------|---------|-------------|--------|
| 80646 | CEREZOS SANTINA 2019 CC-892 (Zuñiga) | 2026-04-08 | Activo |
| 83204 | CEREZOS SANTINA 2014 CC-883 (Zuñiga) | 2026-04-08 | Activo |
| 83605 | CEREZOS LAPINS 2015 CC-884 / RAINIER 2015 CC-882 (Zuñiga) | 2026-04-08 | Activo |
| 88252 | CEREZOS SWEET ARYANA 2023 CC-422 (Isla de Maipo) | 2026-04-08 | Activo |
| 88253 | CIRUELOS ADULTOS CC-860 (Zuñiga) | 2026-04-08 | Activo |
| 88257 | CEREZOS SANTINA 2018 CC-895 (Zuñiga) | 2026-04-08 | Activo |
| 88260 | CEREZOS SANTINA 2020 CC-899 (Zuñiga) | 2026-04-08 | Activo |
| 88261 | CEREZOS SANTINA 2020 CC-899 (Zuñiga) | 2026-04-08 | Activo |
| 88736 | CEREZOS LAPINS 2014 CC-881 (Zuñiga) | 2026-04-08 | Activo |
| 88738 | CEREZOS SANTINA 2020 CC-899 (Zuñiga) | 2026-04-08 | Activo |
| 88732 | CEREZOS SANTINA 2019 CC-892 (Zuñiga) | 2026-03-30 | Inactivo — sin datos hace +9 días |
| 88737 | CEREZOS RAINIER 2023 CC-431 (Isla de Maipo) | 2025-12-21 | Inactivo — sin datos desde dic 2025 |
| 88811 | CEREZOS RED PACIFIC CC-421 (Isla de Maipo) | 2025-12-18 | Inactivo — sin datos desde dic 2025 |
| 87975 | CEREZOS SANTINA 2019 CC-892 (Zuñiga) | 2025-09-11 | Inactivo — sin datos desde sep 2025 |
| 88733 | CEREZOS LAPINS 2014 CC-881 (Zuñiga) | 2025-08-30 | Inactivo — sin datos desde ago 2025 |
| 88424 | CEREZOS LAPINS 2014 CC-881 (Zuñiga) | 2025-08-22 | Inactivo — sin datos desde ago 2025 |
| 88813 | CEREZOS GLOW 2023 CC-426 (Isla de Maipo) | 2025-05-20 | Inactivo — sin datos desde may 2025 |
| 88816 | CEREZOS SANTINA 2023 CC-424 (Isla de Maipo) | 2025-01-16 | Inactivo — sin datos desde ene 2025 |

> **NULLs esperados:** Cada dispositivo solo tiene instalados los sensores físicos que le corresponden. Una columna NULL simplemente indica que ese dispositivo no tiene ese sensor — no es un error de datos.

**Restricción única:** `(channel_id, orchard, date, hour)` — un registro por dispositivo, cuartel y hora.

**Ejemplo de uso:**
```sql
-- Temperatura y humedad del último mes para Isla de Maipo
SELECT date, hour, irrigation_sector, orchard, temperature, humidity,
       humedad_suelo_25cm, humedad_suelo_50cm
FROM ubi_sensor_pivot
WHERE field = 'ISLA DE MAIPO'
  AND date >= CURRENT_DATE - 30
ORDER BY date DESC, hour DESC;
```

---

### `wc_kc_weekly` — Kc semanal por sector

**Propósito:** Tabla precalculada con el coeficiente de cultivo (Kc) semanal por sector de riego. Combina `wc_farms_realirrigation` (riego ejecutado) con `wc_zones_sensors` (Et0) y `field_sectors`. Cubre todos los predios desde agosto 2025.

Se actualiza con `refresh_wc_kc_weekly()` tras cada sync exitoso de Wiseconn.

**Registros:** ~580 | **Rango:** ago 2025 → hoy

#### ¿Qué es el Kc?

**Kc (Coeficiente de Cultivo)** es un número adimensional que responde a: **¿cuánta agua aplicamos en relación a lo que el clima demandó esa semana?**

```
Kc = SUM(irrigated_mm) ÷ SUM(et0_mm)   — acumulado semanal
```

| Valor Kc | Significado |
|----------|-------------|
| `= 1.0` | Regamos exactamente lo que la atmósfera demandó |
| `0.6–1.0` | Rango normal para cerezos/ciruelos en plena temporada |
| `< 0.4` en plena temporada | Posible déficit hídrico o riego no registrado |
| `> 1.2` | Sobreirrigación — riesgo de asfixia radicular y lixiviación |
| `= 0` con Et0 > 0 | Sin riego esa semana (puede ser planificado) |

El Kc cambia según la **etapa fenológica**: en brotación se riega menos (Kc ~0.45), en engrose de fruta se riega más (Kc ~1.0). Ver tabla FAO-56 más abajo.

> **Kc de Wiseconn vs Kc calculado:** Wiseconn almacena un Kc fijo por zona en `wc_farms_zones.kc` (actualmente `1` en todos los sectores) — es el valor que el agrónomo ingresó para que Wiseconn *programe* el riego. El Kc en `wc_kc_weekly` es diferente: es el Kc *real medido*, calculado con el riego que efectivamente se ejecutó.

#### ¿Para qué sirve?

Es la tabla principal para responder **¿estamos regando bien?** El nivel semanal es la granularidad que el asesor agronómico necesita para evaluar tendencias y tomar decisiones de ajuste de riego sin el ruido de días puntuales sin riego.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Columnas clave | Comentario |
|----------|---------------|------------|
| **Reporte de Kc semanal por cuartel** | `kc`, `orchard`, `week_start` | La consulta principal para reportes agronómicos |
| **Tendencia de riego en la temporada** | `irrigated_mm` a lo largo de las semanas | Ver si el riego sigue la curva esperada del cultivo |
| **Comparar Et0 vs riego** | `et0_mm` vs `irrigated_mm` | Semanas donde la demanda superó lo aplicado |
| **Detectar cuarteles sin riego** | `kc = 0` o `irrigated_mm = 0` | Solo aparecen semanas donde hubo al menos un evento de riego |
| **Comparar entre predios** | `field` | Zuñiga vs Isla de Maipo bajo las mismas condiciones climáticas |

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `field_sector_id` | integer | FK a `field_sectors.id` |
| `week_start` | date | Lunes de la semana (inicio) |
| `week_end` | date | Domingo de la semana (fin) |
| `week_number` | integer | Número de semana ISO del año |
| `year` | integer | Año |
| `field` | text | Campo: `ZUÑIGA` o `ISLA DE MAIPO` |
| `irrigation_sector` | text | Nombre del sector de riego |
| `orchard` | text | Nombre del cuartel |
| `crop_type` | text | `CEREZOS` o `CIRUELOS` |
| `irrigated_mm` | numeric | Suma semanal de mm de riego (calculado por Wiseconn: `volume_m3 / area_m2 × 1000`). |
| `et0_mm` | numeric | Suma semanal de Et0 — MAX por zona EMA por día, luego promedio entre EMAs del predio. Zuñiga: promedio EMA Rainier 2015 + EMA Santina 2020. Isla de Maipo: EMA Isla de Maipo. |
| `kc` | numeric | `SUM(irrigated_mm) ÷ SUM(et0_mm)` de la semana |

**Restricción única:** `(week_start, field, irrigation_sector, orchard)`

> **Nota:** Solo hay filas para semanas con al menos un riego registrado en `wc_farms_realirrigation`. Semanas sin riego no aparecen (Kc implícito = 0).

---

**Rangos de referencia FAO-56 para los cultivos del sistema** (riego por goteo, zona semiárida):

| Cultivo | Kc inicio | Kc desarrollo | Kc mediados | Kc final |
|---------|-----------|---------------|-------------|----------|
| Cerezos | 0.45 | 0.70 | 1.00 | 0.75 |
| Ciruelos | 0.45 | 0.70 | 1.05 | 0.75 |

**Alertas agronómicas:**
- 🟢 `0.6–1.1` → rango normal para plena temporada (engrose/cosecha)
- 🟡 `> 1.2` → sobreirrigación, revisar programación
- 🔴 `< 0.4` en plena temporada → déficit hídrico o riego no registrado en Wiseconn
- `kc = 0` con `et0 > 0` → sin riego esa semana (puede ser planificado)

**Validación temporada ene–mar 2026:**
- Cuarteles con KC coherente: LAPINS 2019, SANTINA 2019/2020 (Zuñiga), GLOW/RAINIER 2023 (Isla de Maipo) → 0.4–0.9
- KC = 0 toda la temporada: LAPINS 2014/2015, RAINIER 2015, SANTINA 2014/2018 (Zuñiga) → riego no registrado en Wiseconn, confirmar con campo
- KC < 0.1: RED PACIFIC CC-421, TULARE CC-450 (Isla de Maipo) → misma situación

---

**Ejemplo de uso:**
```sql
-- Kc semanal por cuartel (temporada reciente)
SELECT week_start, week_end, field, orchard, irrigated_mm, et0_mm, kc
FROM wc_kc_weekly
WHERE week_start >= '2026-01-01'
  AND et0_mm > 0
ORDER BY field, orchard, week_start;
```

---

### `ubi_ambient_temperature` — Temperatura ambiente horaria

**Propósito:** Temperatura ambiente horaria por sector, con relación directa a `field_sectors`. Excluye sensores de túnel (prefijo `T-`).

Se actualiza con `refresh_ubi_ambient_temperature()` tras cada sync exitoso de Ubibot.

**Registros:** ~208.000 | **Rango:** may 2024 → hoy

#### ¿Para qué sirve?

Es la tabla más directa para consultar **temperatura del aire por cuartel**. Ya tiene el nombre del sector y cuartel incorporados, excluye los sensores de túnel que distorsionarían los valores de campo abierto, e incluye min y max horario para análisis de amplitud térmica.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Cómo |
|----------|------|
| **Temperatura horaria por cuartel** | Consulta directa sin joins |
| **Temperatura mínima nocturna** | `MIN(temp_min)` filtrando horas nocturnas — clave para alertas de helada |
| **Temperatura máxima diaria** | `MAX(temp_max)` por día — estrés térmico en verano |
| **Comparar temperatura entre cuarteles** | `GROUP BY orchard` para ver diferencias entre sectores del mismo día |
| **Serie histórica para modelos** | Base de datos para calcular GDA, horas frío, etc. |

```sql
-- Temperatura mínima por cuartel en el último mes (riesgo de helada)
SELECT date, orchard, field,
       MIN(temp_min) AS temp_min_dia,
       MAX(temp_max) AS temp_max_dia,
       AVG(temp_avg) AS temp_promedio
FROM ubi_ambient_temperature
WHERE date >= CURRENT_DATE - 30
GROUP BY date, orchard, field
ORDER BY date DESC, temp_min_dia;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `field_sector_id` | integer | FK a `field_sectors.id` |
| `channel_id` | integer | ID del dispositivo Ubibot |
| `channel_name` | varchar | Nombre del dispositivo |
| `field` | text | Campo |
| `irrigation_sector` | text | Sector de riego |
| `orchard` | text | Cuartel |
| `crop_type` | text | Tipo de cultivo |
| `date` | date | Fecha |
| `hour` | time | Hora |
| `temp_avg` | numeric | Temperatura promedio de la hora (°C) |
| `temp_min` | numeric | Temperatura mínima de la hora (°C) |
| `temp_max` | numeric | Temperatura máxima de la hora (°C) |

**Restricción única:** `(channel_id, orchard, date, hour)`

---

### `ubi_soil_sensors` — Temperatura y humedad del suelo horaria

**Propósito:** Tabla unificada con temperatura y humedad del suelo por sector y profundidad. Reemplaza las antiguas tablas `ubi_soil_humidity` y `ubi_soil_temperature` que fueron fusionadas al tener la misma estructura base. Los valores son el AVG de lecturas de esa hora.

Se actualiza con `refresh_ubi_soil_sensors()` tras cada sync exitoso de Ubibot.

**Registros:** ~204.000 | **Rango:** may 2024 → hoy

#### ¿Para qué sirve?

Permite analizar el **estado hídrico y térmico del suelo** a distintas profundidades por cuartel. Es fundamental para decidir cuándo y cuánto regar — la humedad del suelo a 25 cm indica si las raíces superficiales tienen agua disponible, y a 50 cm muestra si el agua está llegando a la zona radicular profunda.

#### ¿Qué se puede hacer con esta tabla?

| Análisis | Columnas clave | Comentario |
|----------|---------------|------------|
| **Humedad del suelo por profundidad** | `hum_25cm`, `hum_50cm`, `hum_rs485` | Ver si el riego está llegando a las distintas capas del suelo |
| **Temperatura del suelo** | `temp_25cm`, `temp_50cm`, `temp_rs485` | Condición de raíces — importante en invierno y primavera |
| **Seguimiento post-riego** | Serie temporal de `hum_25cm` o `hum_50cm` | Ver cómo sube y baja la humedad tras un evento de riego |
| **Comparar sectores** | `GROUP BY orchard` | Ver cuál cuartel retiene más agua |

> **Recordatorio de calidad:** El `temp_25cm` del canal `88252` (S2 EQ2, Isla de Maipo) reporta valores aberrantes (60–86°C). Ignorar esa columna para ese canal. Ver observaciones de calidad más abajo.

```sql
-- Humedad del suelo en Isla de Maipo, última semana
SELECT date, hour, orchard, hum_25cm, hum_50cm, hum_rs485
FROM ubi_soil_sensors
WHERE field = 'ISLA DE MAIPO'
  AND date >= CURRENT_DATE - 7
ORDER BY date DESC, hour DESC, orchard;
```

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `field_sector_id` | integer | FK a `field_sectors.id` |
| `channel_id` | integer | ID del dispositivo Ubibot |
| `channel_name` | varchar | Nombre del dispositivo |
| `field` / `irrigation_sector` / `orchard` / `crop_type` | text | Datos del sector |
| `date` | date | Fecha |
| `hour` | time | Hora |
| `temp_25cm` | numeric | Temperatura del suelo a 25 cm (°C) |
| `temp_50cm` | numeric | Temperatura del suelo a 50 cm (°C) |
| `temp_rs485` | numeric | Temperatura del suelo vía RS485 (°C) |
| `hum_10cm` | numeric | Humedad del suelo a 10 cm (%) |
| `hum_15cm` | numeric | Humedad del suelo a 15 cm (%) |
| `hum_20cm` | numeric | Humedad del suelo a 20 cm (%) |
| `hum_25cm` | numeric | Humedad del suelo a 25 cm (%) |
| `hum_30cm` | numeric | Humedad del suelo a 30 cm (%) |
| `hum_40cm` | numeric | Humedad del suelo a 40 cm (%) |
| `hum_50cm` | numeric | Humedad del suelo a 50 cm (%) |
| `hum_rs485` | numeric | Humedad del suelo vía RS485 (%) |

**Restricción única:** `(channel_id, orchard, date, hour)`

> **Observación — temperatura de suelo:** El sensor `temp_25cm` del canal `88252` (S2 EQ2, Isla de Maipo) reporta valores entre **60–86°C** — físicamente imposible. Sensor fallando (probable desconexión o cortocircuito). **No usar `temp_25cm` de este canal hasta revisión en terreno.** El `temp_50cm` del mismo canal es válido (22–23°C).
>
> **Observación — humedad de suelo:** La mayoría de sensores en Zuñiga reportan `0` constantemente. Solo el canal `88252` (S2 EQ2, Isla de Maipo) tiene datos válidos (25–50%). El canal `89019` (Z-IVU 115 2018) tiene datos válidos pero no está asignado a ningún sector en `field_sectors`.

---

### `ubi_chill_hours` — Horas frío por sector y temporada

**Propósito:** Calcula y acumula las horas frío hora a hora por sector usando tres modelos: HF (horas frío clásico), Utah (porciones frío) y GDA (grados día). La temporada de HF y Utah parte el **1 de mayo**; GDA parte el **1 de agosto**.

Se actualiza con `refresh_ubi_chill_hours()` tras cada sync exitoso de Ubibot.

> **Nota:** el Modelo Dinámico (porciones frío Erez & Fishman) vive en la tabla separada `ubi_chill_portions`, cuya temporada parte el **1 de enero**.

**Registros:** ~250.000 | **Temporadas:** 2024-2025, 2025-2026

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `channel_id` | integer | ID del dispositivo Ubibot |
| `channel_name` | varchar | Nombre del dispositivo |
| `field_sector_id` | integer | FK a `field_sectors.id` |
| `field` | text | Campo |
| `irrigation_sector` | text | Sector de riego |
| `orchard` | text | Cuartel |
| `crop_type` | text | Tipo de cultivo |
| `date` | date | Fecha |
| `hour` | time | Hora |
| `temperature` | numeric | Temperatura ambiente (°C) |
| `hf_value` | smallint | **Horas frío:** `1` si temp ≤ 7.2°C, `0` si no |
| `hf_accumulated` | integer | HF acumuladas desde el **1 de mayo** de la temporada |
| `utah_value` | numeric | **Modelo Utah:** peso según rango de temperatura (puede ser negativo) |
| `utah_accumulated` | numeric | Porciones Utah acumuladas desde el **1 de mayo** |
| `season` | varchar | Temporada HF/Utah (mayo–abril): `2024-2025` o `2025-2026` |
| `gda_value` | numeric | Calor útil por hora: `MAX(temp - 7, 0) / 24` |
| `gda_accumulated` | numeric | GDA acumulados desde el **1 de agosto** de la temporada |
| `gda_season` | varchar | Temporada GDA (agosto–julio): `2024-2025` o `2025-2026` |
| `rn` | integer | Número de fila dentro de la partición (uso interno) |

**Restricción única:** `(channel_id, field_sector_id, date, hour)` — un registro por sensor, sector y hora.

#### Los tres modelos en esta tabla

| Modelo | Columnas | Período | Uso |
|--------|----------|---------|-----|
| **Horas Frío (HF)** | `hf_value`, `hf_accumulated` | 1 mayo → 30 abril | Simple, siempre confiable |
| **Porciones Frío Utah** | `utah_value`, `utah_accumulated` | 1 mayo → 30 abril | Más preciso que HF, puede ser negativo |
| **Grados Día (GDA)** | `gda_value`, `gda_accumulated` | 1 agosto → 31 julio | Mide calor acumulado post-invierno |

#### Modelo Horas Frío (HF) — el más simple

Desarrollado en la década de 1950, es el más antiguo y fácil de entender. Parte de la observación empírica de que los frutales necesitan un número mínimo de horas bajo 7.2°C para salir correctamente del reposo invernal (dormancia).

**Lógica:** cada hora con temperatura ≤ 7.2°C suma 1 HF; cualquier hora sobre ese umbral suma 0. No distingue entre una hora a 1°C y una a 7°C — ambas cuentan igual. Tampoco penaliza el calor.

**Cuándo usarlo:** referencia rápida, comparación entre temporadas, comunicación con el equipo de campo. Es el modelo que más se entiende intuitivamente.

**Limitación:** sobreestima la eficiencia del frío muy intenso (bajo 2°C) y no considera que el calor diurno puede revertir el efecto del frío nocturno.

```
hf_value = 1  si temperatura ≤ 7.2°C
hf_value = 0  si temperatura > 7.2°C
hf_accumulated = suma de hf_value desde el 1 de mayo
```

#### Modelo Utah (Porciones Frío) — intermedio

Desarrollado por Richardson et al. (1974) en la Universidad de Utah, EE.UU. Mejora el modelo HF reconociendo que no todas las temperaturas frías son igual de efectivas, y que el calor puede **destruir** el frío ya acumulado.

**Lógica:** asigna un peso diferente a cada rango de temperatura. El rango óptimo (2.5–9.1°C) suma 1 porción por hora. Temperaturas muy bajas o muy altas tienen peso reducido o negativo. Si durante el día la temperatura supera los 18°C, se restan porciones del acumulado.

| Rango °C | Peso | Interpretación |
|----------|------|----------------|
| ≤ 1.4 | 0 | Demasiado frío — no es efectivo |
| 1.5 – 2.4 | +0.5 | Frío leve |
| 2.5 – 9.1 | **+1** | Zona óptima de vernalización |
| 9.2 – 12.4 | +0.5 | Frío moderado |
| 12.5 – 15.9 | 0 | Temperatura neutra |
| 16.0 – 18.0 | -0.5 | Calor leve — empieza a revertir |
| > 18.0 | **-1** | Calor — deshace frío acumulado |

**Cuándo usarlo:** es el modelo más usado en Chile para decisiones de manejo (aplicación de frío artificial, timing de rompedores de dormancia). Más preciso que HF en zonas con inviernos templados como Chile Central.

**Limitación:** el acumulado puede volverse negativo si hay olas de calor al inicio de la temporada. En temporadas donde el sensor empezó a registrar tarde (ej: julio en lugar de mayo), el acumulado Utah no es confiable.

#### Grados Día Acumulados (GDA)

Métrica opuesta a las horas frío — mide el **calor acumulado** post-invierno. No mide frío sino el avance fenológico una vez terminado el reposo. A mayor GDA, más avanzado el desarrollo del cultivo (brotación, floración, madurez).

**Cuándo usarlo:** estimar fecha de cosecha, comparar velocidad de desarrollo entre cuarteles y temporadas, calibrar modelos fenológicos.

- **Base:** 7°C (temperatura mínima de crecimiento para cerezos/ciruelos en Chile)
- **Fórmula por hora:** `MAX(temp - 7, 0) / 24`
- **Período:** desde el **1 de agosto** de cada temporada (inicio del calor primaveral)

```
Hora a 25°C → GDA = (25-7)/24 = 0.75
Hora a 10°C → GDA = (10-7)/24 = 0.125
Hora a  5°C → GDA = 0  (bajo la base, no aporta)
```

Valores de referencia temporada 2024-2025 (agosto→abril): ~3.000–3.300 GDA en Zuñiga.

#### Ejemplo de uso

```sql
-- Horas frío y Utah acumuladas al 31/jul 2025 por cuartel (1/mayo → 31/jul)
SELECT field, orchard,
    MAX(hf_accumulated)   AS horas_frio,
    MAX(utah_accumulated) AS utah_acum
FROM ubi_chill_hours
WHERE season = '2025-2026'
  AND date <= '2025-07-31'
GROUP BY field, orchard
ORDER BY field, orchard;

-- Curva diaria de HF y Utah por sector (para gráfico)
SELECT date,
    MAX(hf_accumulated)   AS hf_acum,
    MAX(utah_accumulated) AS utah_acum,
    MAX(gda_accumulated)  AS gda_acum
FROM ubi_chill_hours
WHERE field_sector_id = 13 AND season = '2025-2026'
GROUP BY date ORDER BY date;

-- Temporada completa HF y GDA por sector
SELECT field, orchard,
    MAX(hf_accumulated)   AS hf_temporada,
    MAX(gda_accumulated)  AS gda_temporada
FROM ubi_chill_hours
WHERE season = '2025-2026'
GROUP BY field, orchard
ORDER BY field, orchard;
```

#### Observaciones de calidad de datos

> **`utah_accumulated` — confiabilidad según temporada:**
>
> - **Temporada 2025-2026:** todos los sensores tienen datos desde el 1 de mayo 2025 → `utah_accumulated` es **confiable**.
> - **Temporada 2024-2025 — Zuñiga** (Sector 1 EQ 2, Sector 1 EQ 3, Sector 3 EQ 2): datos desde mayo 2024 → `utah_accumulated` **confiable**.
> - **Temporada 2024-2025 — Isla de Maipo** y varios de Zuñiga: datos desde **julio-agosto 2024**, no desde mayo → `utah_accumulated` **no confiable** para esa temporada (el verano siguiente resta sin haber acumulado el invierno completo). Usar solo `hf_accumulated` en esos casos.
>
> **`hf_accumulated` es siempre confiable** — nunca es negativo, refleja las horas observadas desde el primer dato disponible.

---

### `ubi_chill_portions` — Porciones frío Modelo Dinámico

**Propósito:** Calcula y acumula las porciones frío según el Modelo Dinámico (Erez & Fishman 1990) hora a hora por sector. A diferencia de HF y Utah, la temporada parte el **1 de enero** de cada año calendario — porque las temperaturas de verano ya inician el estado bioquímico del modelo.

Se actualiza con `refresh_ubi_chill_portions()` tras cada sync exitoso de Ubibot.

**Registros:** ~250.700 | **Años calendario:** 2024, 2025, 2026

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `channel_id` | integer | ID del dispositivo Ubibot |
| `channel_name` | varchar | Nombre del dispositivo |
| `field_sector_id` | integer | FK a `field_sectors.id` |
| `field` | text | Campo |
| `irrigation_sector` | text | Sector de riego |
| `orchard` | text | Cuartel |
| `crop_type` | text | Tipo de cultivo |
| `date` | date | Fecha |
| `hour` | time | Hora |
| `temperature` | numeric | Temperatura ambiente (°C) |
| `dm_season` | varchar(4) | Año calendario: `'2024'`, `'2025'`, `'2026'` — parte el 1 de enero |
| `dm_state` | numeric | Estado interno del modelo (fracción de moléculas entre 0 y 1) |
| `dm_value` | numeric | Porciones generadas en esta hora (0 o entero positivo) |
| `dm_accumulated` | numeric | Porciones acumuladas desde el **1 de enero** del año |

**Restricción única:** `(channel_id, field_sector_id, date, hour)`

#### Modelo Dinámico (Erez & Fishman 1990)

El más preciso para estimar requerimientos de frío. Estándar internacional adoptado en Chile para cerezos y ciruelos. Simula el comportamiento bioquímico de la planta: el frío activa moléculas inductoras del reposo; el calor las destruye. Una porción se cuenta cada vez que el estado interno (fracción de moléculas activas) cruza el umbral 1.

**Constantes del modelo:**

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| E1 | 4.150 | Energía de activación (formación) |
| E5 | 1.6 | Estado de equilibrio base |
| E6 | 277 K | Temperatura óptima (3.85°C) |
| E7 | 5.43×10⁻¹⁴ | Coeficiente preexponencial |
| E8 | 8.740 | Energía de activación (tasa de transición) |

**Fórmulas por hora:**
```
T_K         = temperatura + 273.16
ftmprt      = E7 × exp(E8 / T_K)                       ← tasa de transición
xs          = E5 / (1 + exp(-E1 × (1/E6 - 1/T_K)))     ← equilibrio
state_nuevo = state + (xs - state) × (1 - exp(-ftmprt))
porcion     = FLOOR(state_nuevo)    ← parte entera = porciones ganadas esta hora
state       = state_nuevo - porcion ← parte decimal continúa al próximo ciclo
```

**Función SQL:** `calc_dm_portions(channel_id, field_sector_id, dm_season)` — recorre todas las horas del año calendario en secuencia, manteniendo el estado entre horas.

#### Por qué la temporada empieza el 1/enero

El modelo dinámico es continuo: el estado bioquímico de verano (altas temperaturas, estado interno bajo) es el punto de partida del invierno siguiente. Si se iniciara en mayo partiendo de 0, se perdería la información acumulada en verano y las primeras porciones de otoño quedarían subestimadas.

En la práctica, el modelo genera pocas o ninguna porción en enero-abril (temperaturas de verano demasiado altas), pero ese estado bioquímico es necesario para calcular correctamente el otoño e invierno siguientes.

#### Ejemplo de uso

```sql
-- Porciones frío al 31/julio 2025 por cuartel (desde 1/enero 2025)
SELECT field, orchard,
    MAX(dm_accumulated)::int AS porciones_frio
FROM ubi_chill_portions
WHERE dm_season = '2025'
  AND date <= '2025-07-31'
GROUP BY field, orchard
ORDER BY field, orchard;

-- Curva diaria de porciones acumuladas (para gráfico)
SELECT date, MAX(dm_accumulated) AS dm_acum
FROM ubi_chill_portions
WHERE field_sector_id = 13 AND dm_season = '2025'
GROUP BY date ORDER BY date;

-- Detalle hora a hora (equivalente planilla "PF 2025 IVU")
SELECT date, hour, temperature, dm_state, dm_value, dm_accumulated
FROM ubi_chill_portions
WHERE channel_id = 80646 AND field_sector_id = 18
  AND dm_season = '2025'
ORDER BY date, hour;
```

#### Porciones frío al 31/julio 2025 — todos los cuarteles

| Campo | Cuartel | Porciones DM (1/ene–31/jul 2025) |
|-------|---------|----------------------------------|
| ISLA DE MAIPO | CEREZOS GLOW 2023 CC-426 | 295 |
| ISLA DE MAIPO | CEREZOS RAINIER 2023 CC-431 | 380 |
| ISLA DE MAIPO | CEREZOS RED PACIFIC CC-421 | 287 |
| ISLA DE MAIPO | CEREZOS SANTINA 2023 CC-424 | 37 ⚠️ |
| ISLA DE MAIPO | CEREZOS SWEET ARYANA 2023 CC-422 | 269 |
| ZUÑIGA | CEREZOS LAPINS 2014 CC-881 | 364 |
| ZUÑIGA | CEREZOS LAPINS 2015 CC-884 | 365 |
| ZUÑIGA | CEREZOS RAINIER 2015 CC-882 | 365 |
| ZUÑIGA | CEREZOS SANTINA 2014 CC-883 | 366 |
| ZUÑIGA | CEREZOS SANTINA 2018 CC-895 | 302 |
| ZUÑIGA | CEREZOS SANTINA 2019 CC-892 | 423 |
| ZUÑIGA | CEREZOS SANTINA 2020 CC-899 | 435 |
| ZUÑIGA | CIRUELOS ADULTOS CC-860 | 376 |

> ⚠️ **CEREZOS SANTINA 2023 CC-424** (Isla de Maipo): solo 37 porciones — el canal tiene datos muy parciales para 2025. Confirmar con equipo de campo.

---

### `wc_ema` — Clima diario de la Estación Meteorológica Automática

**Propósito:** Una fila por día y predio con los valores climáticos de la EMA (Estación Meteorológica Automática Davis), correctamente agregados desde los registros de 15 minutos de la API de Wiseconn.

Se actualiza con `refresh_wc_ema()` tras cada sync exitoso de Wiseconn.

#### ¿Por qué existe esta tabla?

`wc_zones_sensors` almacena solo el **último valor del día** (snapshot de medianoche) para cada sensor. Para sensores climáticos esto es incorrecto: la radiación solar a medianoche siempre es 0, el viento puede ser 0 a esa hora, etc. `wc_ema` resuelve esto bajando los 96 registros de 15 min del día y aplicando la agregación correcta por sensor.

#### Cobertura

| Predio | Desde | Días disponibles | Estación |
|--------|-------|-----------------|---------|
| ZUÑIGA | 2024-10-27 | ~508 | Davis Envoy — sensores nombrados `* - EMA` |
| ISLA DE MAIPO | 2025-03-31 | ~342 | Davis API — sensores nombrados `* Davis API` |

#### Columnas

| Columna | Tipo | Unidad | Agregación | Fuente Zuñiga | Fuente Isla de Maipo |
|---------|------|--------|-----------|--------------|---------------------|
| `id` | SERIAL PK | — | — | — | — |
| `date` | DATE | — | — | clave | clave |
| `farm_id` | VARCHAR | — | — | `14245` | `60544` |
| `field` | TEXT | — | — | `ZUÑIGA` | `ISLA DE MAIPO` |
| `temperatura_c` | DOUBLE | °C | AVG diario | `Temperatura - EMA` | `Temperatura Davis API` |
| `humedad_relativa_pct` | DOUBLE | % | AVG diario | `Humedad Relativa - EMA` | `Humedad Relativa Davis API` |
| `presion_atmosferica_pa` | DOUBLE | Pa | AVG diario | `Presión Atmosférica - EMA` | `Presion Davis API` |
| `radiacion_solar_wm2` | DOUBLE | W/m² | MAX diario | `Radiacion Solar - EMA` | `Radiación Davis API` |
| `pluviometria_mm` | DOUBLE | mm | MAX diario | `Pluviometría - EMA` | `Lluvia Davis API` |
| `velocidad_viento_kmh` | DOUBLE | km/h | AVG diario | `Velocidad Viento - EMA` | `Viento Davis API` |
| `rafaga_viento_kmh` | DOUBLE | km/h | MAX diario | `Rafaga de Viento - EMA` | `Ráfaga Davis API` |
| `direccion_viento_deg` | DOUBLE | ° | AVG diario | `Dirección Viento - EMA` | `Direccion Viento Davis API` |

> **Constraint:** `UNIQUE (date, farm_id)` — un registro por día y predio.

#### ¿Qué se puede hacer con esta tabla?

| Consulta | Columnas |
|----------|---------|
| Temperatura promedio/mín/máx mensual por predio | `temperatura_c`, `date`, `field` |
| Radiación solar acumulada por período | `radiacion_solar_wm2`, `date` |
| Días con lluvia y precipitación acumulada | `pluviometria_mm`, `date` |
| Comparar condiciones climáticas entre Zuñiga e Isla de Maipo | `field`, todos los sensores |
| Correlacionar clima con Kc semanal | JOIN con `wc_kc_weekly` por `farm_id` y semana |

#### Calidad de datos conocida

| Sensor | Zuñiga | Isla de Maipo |
|--------|--------|--------------|
| Temperatura | ✅ Confiable | ✅ Confiable |
| Humedad relativa | ✅ Confiable | ✅ Confiable |
| Presión atmosférica | ✅ Confiable | ✅ Confiable |
| Radiación solar | ✅ Confiable | ✅ Confiable |
| Pluviometría | ⚠️ Subestimado (~60 mm en 16 meses vs ~300 mm/año esperado) | ✅ Aparentemente correcto |
| Velocidad viento | ❌ Casi siempre 0 — anemómetro no funcional | ✅ Datos reales (avg ~2 km/h) |
| Ráfaga viento | ❌ Dañado desde 30-mar-2025 — valor fijo 410 km/h | ✅ Datos reales (max ~35 km/h) |

#### Ejemplos de uso

```sql
-- Temperatura mensual por predio en 2025
SELECT
  field,
  TO_CHAR(date, 'YYYY-MM') AS mes,
  ROUND(AVG(temperatura_c)::numeric, 1) AS temp_avg,
  ROUND(MIN(temperatura_c)::numeric, 1) AS temp_min,
  ROUND(MAX(temperatura_c)::numeric, 1) AS temp_max
FROM wc_ema
WHERE date BETWEEN '2025-01-01' AND '2025-12-31'
GROUP BY field, mes
ORDER BY field, mes;

-- Radiación solar máxima mensual comparada entre predios
SELECT
  TO_CHAR(date, 'YYYY-MM') AS mes,
  ROUND(MAX(radiacion_solar_wm2) FILTER (WHERE field = 'ZUÑIGA')::numeric, 0)        AS rad_zuniga,
  ROUND(MAX(radiacion_solar_wm2) FILTER (WHERE field = 'ISLA DE MAIPO')::numeric, 0) AS rad_imaipo
FROM wc_ema
GROUP BY mes
ORDER BY mes;

-- Días con lluvia registrada
SELECT date, field, pluviometria_mm
FROM wc_ema
WHERE pluviometria_mm > 0
ORDER BY date DESC;
```

---

## Resumen de volumen de datos

| Tabla | Registros | Rango disponible |
|-------|-----------|-----------------|
| `ubi_channels_fields` | ~2.530.000 | may 2024 → hoy |
| `ubi_channel_summary` | ~280.000 | may 2024 → hoy |
| `ubi_sensor_pivot` | ~213.000 | may 2024 → hoy |
| `ubi_ambient_temperature` | ~208.000 | may 2024 → hoy |
| `ubi_soil_sensors` | ~204.000 | may 2024 → hoy |
| `wc_zones_sensors` | ~313.000 | ago 2024 → hoy |
| `wc_farms_realirrigation` | ~6.700 | dic 2023 → hoy |
| `wc_farms_irrigation` | ~6.200 | dic 2023 → hoy |
| `wc_kc_weekly` | ~580 | ago 2025 → hoy |
| `wc_ema` | ~850 (508 Zuñiga + 342 Isla de Maipo) | oct 2024 → hoy |
| `ubi_chill_hours` | ~250.000 | may 2024 → hoy |
| `ubi_chill_portions` | ~250.700 | ene 2024 → hoy |
| `execution_log` | ~12.500 | jun 2024 → hoy |
| `field_sectors` | 22 | — |
| `wc_farms_zones` | 24 | — |
| `ubi_channel_data` | 25 | — |

---

## Sensores pendientes de confirmar

**Sectores sin sensor Ubibot identificado** (requiere confirmación del equipo de terreno):
- Zuñiga — Sector 3 EQ 3 (Lap19) / CEREZOS LAPINS 2019 CC-891
- Zuñiga — Sector 4 EQ 1 (Cer 24) / CEREZOS GLOW
- Isla de Maipo — S1 EQ1 (Tul) / CIRUELAS TULARE CC-450
- Isla de Maipo — S4 EQ2 / CIRUELAS TULARE CC-450

**Canales Ubibot sin sector asignado** (existen en el sistema pero no se identificó a qué cuartel pertenecen):

| Canal ID | Nombre | Campo |
|----------|--------|-------|
| 88158 | T-Peonias | Isla de Maipo |
| 88155 | T-Peonias Sin Malla | Isla de Maipo |
| 88251 | T-Peonías Ensayo 3 | Isla de Maipo |
| 88259 | T-Pimentónes Macro Tunel | Isla de Maipo |
| 88271 | T-Túnel Peonías Ensayo 1 | Isla de Maipo |
| 89019 | Z-IVU 115 2018 | Zuñiga |
| 71208 | Z-Kiwi | Zuñiga |
