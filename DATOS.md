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
                                      └──▶ ubi_channels_fields     (lecturas por sensor)

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

## Resumen de volumen de datos

| Tabla | Registros | Rango disponible |
|-------|-----------|-----------------|
| `ubi_channels_fields` | ~2.530.000 | may 2024 → hoy |
| `ubi_channel_summary` | ~280.000 | may 2024 → hoy |
| `wc_zones_sensors` | ~313.000 | ago 2024 → hoy |
| `wc_farms_realirrigation` | ~6.700 | dic 2023 → hoy |
| `wc_farms_irrigation` | ~6.200 | dic 2023 → hoy |
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
