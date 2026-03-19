# Guía de Datos — Sistema de Integración Donar

Este documento explica qué datos recopila el sistema, de dónde vienen, cómo se organizan en la base de datos y qué significa cada tabla y columna. Está pensado para personas que trabajan con los reportes y necesitan entender la información disponible.

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
                                      └──▶ ubi_sensor_pivot        (pivot para reportes — 20 sensores como columnas)

execution_log  (registro de cada ejecución del sistema)
```

---

## Tablas de referencia

### `field_sectors` — Tabla maestra de sectores

**Propósito:** Fuente única de verdad que conecta cada sector de riego con sus datos de Wiseconn y sus sensores Ubibot. Tiene 22 filas — una por sector de riego.

**Registros:** 22

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

### `wc_zones_sensors` — Lecturas de sensores

**Propósito:** Almacena el **último valor** de cada sensor en cada ejecución del pipeline. **No es una tabla de series de tiempo** — no guarda el historial completo de cada sensor, solo el snapshot más reciente cuando el pipeline corrió. Para Et0 y Etc, el valor del día es el acumulado diario (máximo del día).

**Registros:** ~313.000 | **Rango:** ago 2024 → hoy

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `sensor_id` | varchar | ID del sensor en Wiseconn (formato `"6-53361-1"`) |
| `name` | text | Nombre del sensor: `Et0`, `Etc`, `Temperature`, `Humidity`, `Irrigation Precipitation`, `Caudalimetro EQ1`, etc. |
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
```

---

### `wc_farms_realirrigation` — Riego real ejecutado

**Propósito:** Registra cada evento de riego **realmente ejecutado** en el campo. Es la fuente de verdad para saber cuánto se regó, cuándo y en qué sector. Cada fila es un evento de riego completo con inicio, fin y volúmenes medidos.

**Registros:** ~6.700 | **Rango:** dic 2023 → hoy

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

### `ubi_channel_data` — Catálogo de dispositivos Ubibot

**Propósito:** Catálogo con un registro por dispositivo Ubibot. Se sobreescribe en cada ejecución con los datos actuales del dispositivo.

**Registros:** 25

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

## Funciones de reporte disponibles

### `f_kc(p_fecha_desde, p_fecha_hasta, p_field[], p_orchard[])` — Coeficiente de cultivo

Función principal de reportería. Combina `wc_farms_realirrigation` + `field_sectors` + `wc_zones_sensors` (Et0) para calcular el Kc diario por cuartel. El Et0 de Zuñiga es el promedio de las 2 EMAs.

```sql
-- Todos los cuarteles
SELECT * FROM f_kc('2026-03-01', '2026-03-17');

-- Solo Zuñiga
SELECT * FROM f_kc('2026-03-01', '2026-03-17', ARRAY['ZUÑIGA']);

-- Un cuartel específico
SELECT * FROM f_kc('2026-03-01', '2026-03-17', NULL, ARRAY['CEREZOS LAPINS 2014 CC-881']);
```

| Columna | Descripción |
|---------|-------------|
| `fecha` | Fecha |
| `field` | Campo (ZUÑIGA / ISLA DE MAIPO) |
| `orchard` | Nombre del cuartel |
| `crop_type` | CEREZOS o CIRUELOS |
| `irrigated_mm` | Milímetros de riego aplicados |
| `et0_mm` | Et0 promedio del campo ese día |
| `kc` | `irrigated_mm ÷ et0_mm` |

| Kc | Interpretación |
|----|----------------|
| 0 (con Et0 > 0) | Sin riego ese día |
| 0.7 – 1.1 | Rango normal en plena temporada |
| > 1.5 | Posible sobreirrigación |
| < 0.3 en temporada alta | Posible déficit hídrico |

---

### `f_ambient_temperature(p_fecha_desde, p_fecha_hasta, p_canales[])` — Temperatura ambiente

Lecturas horarias de temperatura de los sensores Ubibot. Excluye automáticamente sensores de túnel (prefijo `T-`).

```sql
-- Todos los sensores
SELECT * FROM f_ambient_temperature('2026-03-01', '2026-03-17');

-- Sensores específicos
SELECT * FROM f_ambient_temperature('2026-03-01', '2026-03-17', ARRAY['Z-Santina 2014', 'Z-Lapins 2014']);
```

| Columna | Descripción |
|---------|-------------|
| `date` | Fecha |
| `hour` | Hora |
| `channel` | Nombre del dispositivo |
| `channel_id` | ID del dispositivo |
| `temp_avg` | Temperatura promedio (°C) |
| `temp_min` | Temperatura mínima (°C) |
| `temp_max` | Temperatura máxima (°C) |

---

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

**Registros:** ~208.000 | **Rango:** may 2024 → hoy

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

### `wc_kc_daily` — Kc diario por sector

**Propósito:** Tabla precalculada con el coeficiente de cultivo (Kc) diario por sector de riego. Combina `wc_farms_realirrigation` (riego ejecutado) con `wc_zones_sensors` (Et0) y `field_sectors`. Reemplaza a la función `f_kc()` como fuente de datos — la función ahora lee de esta tabla.

Se actualiza con `refresh_wc_kc_daily()` tras cada sync exitoso de Wiseconn.

**Registros:** ~4.900 | **Rango:** oct 2024 → hoy

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `field_sector_id` | integer | FK a `field_sectors.id` |
| `date` | date | Fecha |
| `field` | text | Campo: `ZUÑIGA` o `ISLA DE MAIPO` |
| `irrigation_sector` | text | Nombre del sector de riego |
| `orchard` | text | Nombre del cuartel |
| `crop_type` | text | `CEREZOS` o `CIRUELOS` |
| `irrigated_mm` | numeric | Milímetros de riego aplicados ese día |
| `et0_mm` | numeric | Et0 promedio del campo ese día (promedio de todas las EMAs) |
| `kc` | numeric | `irrigated_mm ÷ et0_mm` |

**Restricción única:** `(date, field, irrigation_sector, orchard)` — necesaria porque algunos orchards tienen múltiples sectores de riego (ej: CIRUELOS ADULTOS CC-860 tiene 3 sectores en Zuñiga).

> **Nota:** Solo hay filas para días con riego registrado en `wc_farms_realirrigation`. Días sin riego no aparecen en la tabla (Kc implícito = 0).

**Ejemplo de uso:**
```sql
-- Kc semanal por cuartel
SELECT date, field, orchard, irrigated_mm, et0_mm, kc
FROM wc_kc_daily
WHERE date BETWEEN '2026-03-01' AND '2026-03-18'
ORDER BY date, field, orchard;

-- O usando la función (equivalente, incluye filtros opcionales)
SELECT * FROM f_kc('2026-03-01', '2026-03-18', ARRAY['ZUÑIGA']);
```

---

### `ubi_ambient_temperature` — Temperatura ambiente horaria

**Propósito:** Temperatura ambiente horaria por sector, con relación directa a `field_sectors`. Fuente de la función `f_ambient_temperature()`. Excluye sensores de túnel (prefijo `T-`).

Se actualiza con `refresh_ubi_ambient_temperature()` tras cada sync exitoso de Ubibot.

**Registros:** ~208.000 | **Rango:** may 2024 → hoy

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

### `ubi_soil_humidity` — Humedad del suelo horaria

**Propósito:** Humedad del suelo horaria por sector, capturando todas las profundidades disponibles como columnas separadas. Los valores son el AVG de lecturas de esa hora.

Se actualiza con `refresh_ubi_soil_humidity()` tras cada sync exitoso de Ubibot.

**Registros:** ~204.000 | **Rango:** may 2024 → hoy

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Clave primaria |
| `field_sector_id` | integer | FK a `field_sectors.id` |
| `channel_id` | integer | ID del dispositivo Ubibot |
| `channel_name` | varchar | Nombre del dispositivo |
| `field` / `irrigation_sector` / `orchard` / `crop_type` | text | Datos del sector |
| `date` | date | Fecha |
| `hour` | time | Hora |
| `hum_10cm` | numeric | Humedad del suelo a 10 cm (%) |
| `hum_15cm` | numeric | Humedad del suelo a 15 cm (%) |
| `hum_20cm` | numeric | Humedad del suelo a 20 cm (%) |
| `hum_25cm` | numeric | Humedad del suelo a 25 cm (%) |
| `hum_30cm` | numeric | Humedad del suelo a 30 cm (%) |
| `hum_40cm` | numeric | Humedad del suelo a 40 cm (%) |
| `hum_50cm` | numeric | Humedad del suelo a 50 cm (%) |
| `hum_rs485` | numeric | Humedad del suelo vía RS485 (%) |

**Restricción única:** `(channel_id, orchard, date, hour)`

> **Observación de calidad de datos:** La mayoría de sensores de humedad de suelo en Zuñiga reportan `0` constantemente — posible falla de hardware o sensor desconectado. Solo el canal `88252` (S2 EQ2, Isla de Maipo) tiene datos válidos activos con valores en el rango esperado (25–50%). Confirmar estado de sensores con equipo de terreno.
>
> El canal `89019` (Z-IVU 115 2018, Zuñiga) tiene datos de humedad de suelo válidos pero **no está asignado a ningún sector** en `field_sectors`, por lo que no aparece en esta tabla.

---

### `ubi_soil_temperature` — Temperatura del suelo horaria

**Propósito:** Temperatura del suelo horaria por sector a distintas profundidades. Los valores son el AVG de lecturas de esa hora.

Se actualiza con `refresh_ubi_soil_temperature()` tras cada sync exitoso de Ubibot.

**Registros:** ~204.000 | **Rango:** may 2024 → hoy

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

**Restricción única:** `(channel_id, orchard, date, hour)`

> **Observación de calidad de datos — sensor defectuoso:**
> El sensor `temp_25cm` del canal `88252` (S2 EQ2, Isla de Maipo) reporta valores entre **60–86°C**, lo cual es físicamente imposible para temperatura de suelo. El sensor a 25 cm está fallando — probable desconexión física, cortocircuito en la sonda, o calibración perdida. **No usar `temp_25cm` de este canal para reportes hasta que sea revisado por el equipo de terreno.**
>
> El sensor `temp_50cm` del mismo canal reporta valores válidos (22–23°C). Los sensores de Zuñiga reportan `0` (misma situación que humedad de suelo).

---

### `ubi_chill_hours` — Horas frío por sector y temporada

**Propósito:** Calcula y acumula las horas frío hora a hora por sector, usando dos modelos estándar de la industria frutícola. Permite generar el reporte de HF acumuladas por temporada (equivalente a la planilla "Horas Frío IVU") directamente desde la base de datos.

Se actualiza con `refresh_ubi_chill_hours()` tras cada sync exitoso de Ubibot.

**Registros:** ~243.000 | **Temporadas:** 2024-2025, 2025-2026

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
| `hf_value` | smallint | **Modelo Utah simplificado:** `1` si temp ≤ 7.2°C, `0` si no |
| `hf_accumulated` | integer | HF acumuladas desde el 1 de mayo de la temporada |
| `utah_value` | numeric | **Modelo Utah completo:** peso según rango de temperatura |
| `utah_accumulated` | numeric | Utah acumulado desde el 1 de mayo de la temporada |
| `season` | varchar | Temporada: `2024-2025` o `2025-2026` |
| `rn` | integer | Número de fila dentro de la partición (uso interno) |

**Restricción única:** `(channel_id, field_sector_id, date, hour)` — un registro por sensor, sector y hora. Un canal que cubre múltiples sectores genera una fila por sector.

#### Modelo Utah simplificado

Cada hora con temperatura ≤ 7.2°C suma 1 HF. Simple y ampliamente usado en Chile.

#### Modelo Utah completo (pesos por rango)

Más preciso — el frío óptimo está entre 2.5–9.1°C. El calor resta horas acumuladas:

| Rango °C | Peso |
|----------|------|
| ≤ 1.4 | 0 — demasiado frío |
| 1.5 – 2.4 | +0.5 |
| 2.5 – 9.1 | **+1** — zona óptima |
| 9.2 – 12.4 | +0.5 |
| 12.5 – 15.9 | 0 |
| 16.0 – 18.0 | -0.5 |
| > 18.0 | **-1** — el calor deshace frío acumulado |

#### Ejemplo de uso

```sql
-- HF acumuladas al día de hoy por sector, temporada actual
SELECT irrigation_sector, orchard, MAX(hf_accumulated) AS hf_hoy, MAX(utah_accumulated) AS utah_hoy
FROM ubi_chill_hours
WHERE season = '2025-2026'
GROUP BY irrigation_sector, orchard
ORDER BY hf_hoy DESC;

-- Curva diaria de acumulación (para gráfico)
SELECT date, MAX(hf_accumulated) AS hf_acum, MAX(utah_accumulated) AS utah_acum
FROM ubi_chill_hours
WHERE field_sector_id = 13 AND season = '2025-2026'
GROUP BY date ORDER BY date;
```

#### Totales por temporada (referencia)

| Sensor | Temporada | Inicio datos | HF total | Utah total | Confiable |
|--------|-----------|-------------|----------|------------|-----------|
| Sector 1 EQ 3 (San19s) | 2024-2025 | 01/05/2024 | 1.321 | 748 | ✅ |
| Sector 3 EQ 2 (Rai15) | 2024-2025 | 10/05/2024 | 1.417 | 877 | ✅ |
| Sector 1 EQ 2 (San14) | 2024-2025 | 02/05/2024 | 1.227 | 429 | ✅ |
| S2 EQ2 | 2024-2025 | 29/07/2024 | 347 | — | ⚠️ parcial |
| S2 EQ1 | 2024-2025 | 06/08/2024 | 221 | — | ⚠️ parcial |
| Sector 1 EQ 1 (Dag) | 2025-2026 | 01/05/2025 | 1.336 | 1.113 | ✅ |
| Sector 3 EQ 2 (Rai15) | 2025-2026 | 01/05/2025 | 1.275 | 904 | ✅ |
| S2 EQ1 | 2025-2026 | 01/05/2025 | 1.196 | 1.046 | ✅ |
| S2 EQ2 | 2025-2026 | 01/05/2025 | 1.099 | 864 | ✅ |

#### Observaciones de calidad de datos

> **`utah_accumulated` — confiabilidad según temporada:**
>
> - **Temporada 2025-2026:** todos los sensores tienen datos desde el 1 de mayo 2025 → `utah_accumulated` es **confiable**.
> - **Temporada 2024-2025 — Zuñiga** (Sector 1 EQ 2, Sector 1 EQ 3, Sector 3 EQ 2): datos desde mayo 2024 → `utah_accumulated` **confiable**.
> - **Temporada 2024-2025 — Isla de Maipo** (S2 EQ1, S2 EQ2, S3 EQ1, S3 EQ2) y varios de Zuñiga: datos desde **julio-agosto 2024**, no desde mayo → `utah_accumulated` **no confiable** para esa temporada (arroja valores negativos por el verano siguiente que resta sin haber acumulado el invierno completo). Usar solo `hf_accumulated` para esos casos.
>
> **`hf_accumulated` es siempre confiable** — nunca es negativo, solo refleja las horas efectivamente observadas desde el primer dato disponible.

---

## Resumen de volumen de datos

| Tabla | Registros | Rango disponible |
|-------|-----------|-----------------|
| `ubi_channels_fields` | ~2.530.000 | may 2024 → hoy |
| `ubi_channel_summary` | ~280.000 | may 2024 → hoy |
| `ubi_sensor_pivot` | ~208.000 | may 2024 → hoy |
| `ubi_ambient_temperature` | ~208.000 | may 2024 → hoy |
| `ubi_soil_humidity` | ~204.000 | may 2024 → hoy |
| `ubi_soil_temperature` | ~204.000 | may 2024 → hoy |
| `wc_zones_sensors` | ~313.000 | ago 2024 → hoy |
| `wc_farms_realirrigation` | ~6.700 | dic 2023 → hoy |
| `wc_farms_irrigation` | ~6.200 | dic 2023 → hoy |
| `wc_kc_daily` | ~4.900 | oct 2024 → hoy |
| `ubi_chill_hours` | ~243.000 | may 2024 → hoy |
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
