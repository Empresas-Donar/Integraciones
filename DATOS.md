# Guía de Datos — Sistema de Integración Donar

Este documento explica de forma simple qué datos recopila el sistema, de dónde vienen, cómo se organizan y qué significan. Está pensado para personas que trabajan con los reportes y necesitan entender la información disponible.

---

## ¿Qué hace este sistema?

Cada hora, el sistema se conecta automáticamente a **dos plataformas externas** y descarga todos los datos de sensores y riego de los dos campos de Empresas Donar. Esos datos se guardan en una base de datos central desde donde se generan los reportes.

```
Wiseconn (control de riego)  ──┐
                                ├──▶  Base de datos Donar  ──▶  Reportes
Ubibot (sensores ambientales) ──┘
```

Desde su puesta en marcha, el sistema ha realizado más de **12.000 ejecuciones automáticas**.

---

## Los dos campos

| Campo | Ubicación | ID en sistema |
|-------|-----------|---------------|
| **Zuñiga** | Región del Libertador | 14245 |
| **Isla de Maipo** | Región Metropolitana | 60544 |

---

## Fuente 1: Wiseconn — Control de Riego

**Wiseconn** es la plataforma que controla y registra el riego de cada sector del campo. Funciona como el "cerebro" del sistema de riego: programa los riegos, los ejecuta y registra exactamente cuánto se regó.

### ¿Qué datos entrega?

| Dato | Qué significa | Unidad |
|------|--------------|--------|
| **Riego ejecutado** | Cuánto se regó realmente en cada sector | mm / m³ |
| **Et0** | Evapotranspiración de referencia: la sed de la atmósfera ese día | mm/día |
| **Etc** | Lo que el cultivo realmente necesita (Et0 × Kc del cultivo) | mm/día |
| **Temperatura** | Temperatura del aire medida en la EMA | °C |
| **Humedad relativa** | Humedad del ambiente | % |
| **Radiación solar** | Energía solar que llega al cultivo | W/m² |
| **Velocidad del viento** | Velocidad y dirección del viento | m/s |
| **Lluvia** | Precipitación registrada | mm |
| **Horas frío** | Acumulado de horas bajo 7.2°C (necesario para cerezos y ciruelos) | horas |
| **Grados día** | Acumulado de calor desde la brotación | °C/día |
| **Caudales y presiones** | Estado de los equipos de bombeo y riego | m³/h / bar |

> **EMA** = Estación Meteorológica Automática. Zuñiga tiene 2 EMAs (Rainier 2015 y Santina 2020). Isla de Maipo tiene 1 EMA.

### ¿Dónde se guardan en la base de datos?

| Tabla | Qué contiene |
|-------|-------------|
| `wc_farms_zones` | Catálogo de sectores de riego de cada campo |
| `wc_zones_sensors` | Lecturas de todos los sensores (~313.000 registros) |
| `wc_farms_irrigation` | Programas de riego (lo planificado) |
| `wc_farms_realirrigation` | Riego real ejecutado (~6.500 eventos) |

---

## Fuente 2: Ubibot — Sensores Ambientales

**Ubibot** son pequeños dispositivos físicos instalados dentro de los cuarteles que miden el ambiente y el suelo en tiempo real. Cada dispositivo se llama **canal** y puede tener varios sensores.

### ¿Qué miden?

| Tipo de medición | Ejemplos |
|-----------------|----------|
| **Clima** | Temperatura y humedad del aire |
| **Suelo** | Humedad del suelo a 25 cm y 50 cm de profundidad, temperatura del suelo |
| **Otros** | CO₂, luz, conductividad eléctrica del suelo |

Los datos se guardan cada hora como promedio, mínimo y máximo del período.

### ¿Cuántos dispositivos hay por campo?

| Campo | Dispositivos Ubibot |
|-------|---------------------|
| Zuñiga | 16 canales distribuidos en 12 sectores |
| Isla de Maipo | 6 canales distribuidos en 6 sectores |

> Algunos sectores tienen más de un dispositivo para cubrir mayor superficie (ej: Lapins 2014 en Zuñiga tiene 3 sensores).

### ¿Dónde se guardan en la base de datos?

| Tabla | Qué contiene |
|-------|-------------|
| `ubi_channel_data` | Catálogo de dispositivos Ubibot (nombre, coordenadas) |
| `ubi_channel_summary` | Registro horario por dispositivo (~26.000 registros) |
| `ubi_channels_fields` | Lecturas de cada sensor con avg/min/max (~2.500.000 registros) |

---

## La tabla maestra: `field_sectors`

Esta es la **tabla central** que conecta los sectores de riego con los datos de Wiseconn y los sensores de Ubibot. Es la única fuente de verdad para saber qué cuartel corresponde a qué sector y qué sensores lo monitorean.

### ¿Qué tiene cada fila?

| Columna | Qué significa | Ejemplo |
|---------|--------------|---------|
| `field` | Nombre del campo | ZUÑIGA |
| `farm_id` | ID del **campo** en Wiseconn | 14245 |
| `irrigation_sector` | Nombre del sector en Wiseconn | Sector 2 EQ 2 (Lap14) |
| `wc_zone_id` | ID del **sector** en Wiseconn | 50927 |
| `orchard` | Nombre del cuartel (variedad + año + código) | CEREZOS LAPINS 2014 CC-881 |
| `crop_type` | Tipo de cultivo | CEREZOS |
| `ubibot_channel_ids` | IDs de los sensores Ubibot en ese sector | {88424, 88733, 88736} |

> **¿Cuál es la diferencia entre `farm_id` y `wc_zone_id`?**
>
> En Wiseconn, la estructura está organizada en dos niveles:
> - **Campo (farm)** → es el predio completo. Zuñiga tiene `farm_id = 14245` y todo lo de Zuñiga comparte ese mismo ID.
> - **Zona (zone)** → es un sector de riego específico dentro del campo. Cada sector tiene su propio `wc_zone_id` único. Por ejemplo, "Sector 2 EQ 2 (Lap14)" tiene `wc_zone_id = 50927`, mientras que "Sector 1 EQ 1 (Dag)" tiene `wc_zone_id = 50918`.
>
> En pocas palabras: `farm_id` identifica **el campo**, `wc_zone_id` identifica **el sector dentro del campo**.

### ¿Cómo se relaciona con el resto?

```
field_sectors
     │
     ├── wc_zone_id ──────────▶ wc_farms_zones
     │                               │
     │                               ├──▶ wc_zones_sensors (lecturas de sensores)
     │                               └──▶ wc_farms_realirrigation (riego ejecutado)
     │
     └── ubibot_channel_ids ──▶ ubi_channel_data
                                      │
                                      ├──▶ ubi_channel_summary (resúmenes horarios)
                                      └──▶ ubi_channels_fields (lecturas por sensor)
```

---

## Sectores y cuarteles de Zuñiga

Zuñiga tiene **14 sectores de riego** organizados en 3 equipos (EQ1, EQ2, EQ3):

| Sector | Cuartel | Cultivo | Sensores Ubibot |
|--------|---------|---------|-----------------|
| Sector 1 EQ 1 (Dag) | CIRUELOS ADULTOS CC-860 | Ciruelos | 88253 |
| Sector 2 EQ 1 (Dag) | CIRUELOS ADULTOS CC-860 | Ciruelos | 88253 |
| Sector 3 EQ 1 (Dag) | CIRUELOS ADULTOS CC-860 | Ciruelos | 88253 |
| Sector 1 EQ 2 (San14) | CEREZOS SANTINA 2014 CC-883 | Cerezos | 83204 |
| Sector 2 EQ 2 (Lap14) | CEREZOS LAPINS 2014 CC-881 | Cerezos | 88424, 88733, 88736 |
| Sector 3 EQ 2 (Rai15) | CEREZOS LAPINS 2015 CC-884 | Cerezos | 83605 |
| Sector 3 EQ 2 (Rai15) | CEREZOS RAINIER 2015 CC-882 | Cerezos | 83605 |
| Sector 4 EQ 2 (San18) | CEREZOS SANTINA 2018 CC-895 | Cerezos | 88257 |
| Sector 1 EQ 3 (San19s) | CEREZOS SANTINA 2019 CC-892 | Cerezos | 80646 |
| Sector 2 EQ 3 (San19n) | CEREZOS SANTINA 2019 CC-892 | Cerezos | 87975, 88732 |
| Sector 3 EQ 3 (Lap19) | CEREZOS LAPINS 2019 CC-891 | Cerezos | _(pendiente)_ |
| Sector 4 EQ 1 (Cer 24) | CEREZOS GLOW | Cerezos | _(pendiente)_ |
| Sector 4 EQ 3 (San20s) | CEREZOS SANTINA 2020 CC-899 | Cerezos | 88260, 88738 |
| Sector 5 EQ 3 (San20n) | CEREZOS SANTINA 2020 CC-899 | Cerezos | 88261 |

> Los 3 sectores EQ1 (Dag) riegan el mismo cuartel de ciruelos adultos con distintos equipos. Comparten el sensor Ubibot 88253.
> El sector 3 EQ2 (Rai15) tiene dos cuarteles distintos (Lapins y Rainier 2015) que se riegan juntos.

---

## Sectores y cuarteles de Isla de Maipo

Isla de Maipo tiene **8 sectores de riego** organizados en 2 equipos (EQ1, EQ2):

| Sector | Cuartel | Cultivo | Sensores Ubibot |
|--------|---------|---------|-----------------|
| S1 EQ1 (Tul) | CIRUELAS TULARE CC-450 | Ciruelos | _(pendiente)_ |
| S4 EQ2 | CIRUELAS TULARE CC-450 | Ciruelos | _(pendiente)_ |
| S1 EQ2 | CEREZOS RED PACIFIC CC-421 | Cerezos | 88811 |
| S2 EQ1 (Glow) | CEREZOS GLOW 2023 CC-426 | Cerezos | 88813 |
| S2 EQ2 | CEREZOS SWEET ARYANA 2023 CC-422 | Cerezos | 88252 |
| S3 EQ1 | CEREZOS SANTINA 2023 CC-424 | Cerezos | 88816 |
| S3 EQ2 | CEREZOS RED PACIFIC CC-421 | Cerezos | 88811 |
| S4 EQ1 | CEREZOS RAINIER 2023 CC-431 | Cerezos | 88737 |

> Los sectores S1 EQ2 y S3 EQ2 corresponden al mismo cuartel Red Pacific y comparten el sensor Ubibot 88811.

---

## Funciones de reporte disponibles

Las funciones son consultas parametrizadas en la base de datos. Se llaman con un rango de fechas y opcionalmente filtros adicionales.

### `f_kc` — Coeficiente de cultivo diario

Función principal de reportería. Combina el riego ejecutado (Wiseconn) con la evapotranspiración Et0 para calcular el Kc de cada cuartel.

```sql
-- Todos los cuarteles entre fechas
SELECT * FROM f_kc('2026-03-01', '2026-03-16');

-- Solo Zuñiga
SELECT * FROM f_kc('2026-03-01', '2026-03-16', ARRAY['ZUÑIGA']);

-- Un cuartel específico
SELECT * FROM f_kc('2026-03-01', '2026-03-16', NULL, ARRAY['CEREZOS LAPINS 2014 CC-881']);
```

| Columna | Qué muestra |
|---------|------------|
| `fecha` | Fecha del registro |
| `field` | Nombre del campo (ZUÑIGA / ISLA DE MAIPO) |
| `orchard` | Nombre del cuartel |
| `crop_type` | CEREZOS o CIRUELOS |
| `irrigated_mm` | Milímetros de riego aplicados ese día |
| `et0_mm` | Et0 promedio del campo ese día |
| `kc` | irrigated_mm ÷ et0_mm |

**¿Cómo interpretar el Kc?**

| Valor Kc | Qué significa |
|----------|--------------|
| Entre 0.7 y 1.1 | Riego normal y ajustado a la demanda |
| 0 (con Et0 > 0) | No se regó ese día |
| Mayor a 1.5 | Posible sobreirrigación |
| Menor a 0.3 (en plena temporada) | Posible déficit hídrico |
| NULL | Sin dato de Et0 ese día |

### `f_ambient_temperature` — Temperatura ambiente horaria

Lecturas horarias de temperatura de los sensores Ubibot. Filtra automáticamente los sensores de túnel (T-*).

```sql
-- Todos los sensores entre fechas
SELECT * FROM f_ambient_temperature('2026-03-01', '2026-03-16');

-- Canales específicos
SELECT * FROM f_ambient_temperature('2026-03-01', '2026-03-16', ARRAY['Z-Santina 2014', 'Z-Lapins 2014']);
```

| Columna | Qué muestra |
|---------|------------|
| `date` | Fecha |
| `hour` | Hora del registro |
| `channel` | Nombre del dispositivo Ubibot |
| `channel_id` | ID del dispositivo |
| `temp_avg` | Temperatura promedio del período (°C) |
| `temp_min` | Temperatura mínima (°C) |
| `temp_max` | Temperatura máxima (°C) |

---

## Sensores pendientes de confirmar

Los siguientes elementos aún no tienen mapeo completo. Se requiere confirmación del equipo de terreno sobre si existe sensor instalado:

**Sectores sin sensor Ubibot identificado:**
- Zuñiga — Sector 3 EQ 3 (Lap19) / CEREZOS LAPINS 2019 CC-891
- Zuñiga — Sector 4 EQ 1 (Cer 24) / CEREZOS GLOW
- Isla de Maipo — S1 EQ1 (Tul) / CIRUELAS TULARE CC-450
- Isla de Maipo — S4 EQ2 / CIRUELAS TULARE CC-450

**Canales Ubibot sin sector asignado** (existen en el sistema pero no se pudo identificar a qué cuartel pertenecen):

| Canal ID | Nombre | Campo |
|----------|--------|-------|
| 88158 | T-Peonias | Isla de Maipo |
| 88155 | T-Peonias Sin Malla | Isla de Maipo |
| 88251 | T-Peonías Ensayo 3 | Isla de Maipo |
| 88259 | T-Pimentónes Macro Tunel | Isla de Maipo |
| 88271 | T-Túnel Peonías Ensayo 1 | Isla de Maipo |
| 89019 | Z-IVU 115 2018 | Zuñiga |
| 71208 | Z-Kiwi | Zuñiga |

---

## Resumen de volumen de datos

| Tabla | Registros aproximados |
|-------|----------------------|
| Lecturas de sensores Wiseconn | 313.000 |
| Eventos de riego ejecutado | 6.500 |
| Resúmenes horarios Ubibot | 26.000 |
| Lecturas de campos Ubibot | 2.500.000 |
| Ejecuciones del sistema | 12.000+ |
