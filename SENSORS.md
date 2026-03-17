# Mapa de Sensores por Sector

Este documento muestra exactamente qué sensores tiene cada sector de riego, tanto en Wiseconn (control de riego) como en Ubibot (sensores ambientales en terreno). Los datos de sensores Ubibot fueron validados directamente desde la base de datos.

---

## Resumen de cobertura

| | Zuñiga | Isla de Maipo | Total |
|--|--------|---------------|-------|
| Sectores de riego (Wiseconn) | 14 | 8 | 22 |
| EMAs (estaciones meteorológicas) | 2 | 1 | 3 |
| Dispositivos Ubibot asignados | 16 canales en 12 sectores | 6 canales en 6 sectores | 22 |
| Sectores sin Ubibot | 2 | 2 | 4 |

---

## ¿Qué mide cada sistema?

### Wiseconn — sensores de riego (todos los sectores tienen estos)

| Sensor | Qué mide | Unidad |
|--------|---------|--------|
| `Irrigation Precipitation` | Agua de riego aplicada | mm |
| `Irrigation Time` | Duración del riego | min |
| `Irrigation Volume` | Volumen de riego | m³ |
| `Fertigation Time` | Duración de fertirrigación | min |
| `Fertigation Volume` | Volumen de fertirrigación | l |
| `Etc` | Evapotranspiración del cultivo | mm |
| `Caudalimetro EQ1/2/3` | Flujo de agua en el equipo | m³/h |
| `Volumen Acumulado - Caudalimetro` | Volumen total acumulado | m³ |
| `Presión Eq 1/2/3` | Presión en la red de riego _(Zuñiga)_ | bar |
| `Falla de Nivel EQ1/2/3` | Alarma de nivel _(Zuñiga)_ | — |

### EMAs — estaciones meteorológicas (datos climáticos)

| Sensor | Qué mide | Unidad |
|--------|---------|--------|
| `Et0` | Evapotranspiración de referencia | mm/día |
| `Temperatura` | Temperatura del aire | °C |
| `Humedad Relativa` | Humedad del ambiente | % |
| `Radiación Solar` | Energía solar | W/m² |
| `Lluvia / Pluviometría` | Precipitación | mm |
| `Velocidad / Dirección Viento` | Viento | m/s |
| `Presión Atmosférica` | Presión del aire | hPa |
| `Horas frío` | Acumulado de horas bajo 7.2°C | h |
| `Grados día` | Acumulado de calor (base 10°C) | °C·día |

### Ubibot — sensores ambientales en terreno

| Sensor | Qué mide | Unidad |
|--------|---------|--------|
| `Temperature` | Temperatura del aire | °C |
| `Humidity` | Humedad del aire | % |
| `Humedad del suelo (25 cm)` | Agua disponible en el suelo a 25 cm | % |
| `Humedad del suelo (50 cm)` | Agua disponible en el suelo a 50 cm | % |
| `Temperatura del suelo (25 cm)` | Temperatura del suelo a 25 cm | °C |
| `Temperatura del suelo (50 cm)` | Temperatura del suelo a 50 cm | °C |
| `RS485 Soil Moisture` | Humedad de suelo (sonda externa RS485) | % |
| `RS485 Soil Temperature` | Temperatura de suelo (sonda externa RS485) | °C |
| `RS485 Humidity` / `RS485 Temperature` | Humedad/temperatura externa RS485 | % / °C |
| `Carbon Dioxide` / `CO2` | Concentración de CO₂ | ppm |
| `Wind Speed` | Velocidad del viento | m/s |
| `RS485 Atmospheric Pressure` | Presión atmosférica (sonda RS485) | hPa |
| `PT100 Temperature` | Temperatura con sonda PT100 de precisión | °C |
| `Light` / `External Light` | Luz ambiental | lux |
| `Voltage` | Batería del dispositivo | V |
| `GSM RSSI` / `WIFI RSSI` | Señal de conexión | dBm |

---

## Zuñiga — Mapa completo de sensores

### EMAs (estaciones meteorológicas)

| EMA | Sensores climáticos |
|-----|---------------------|
| **EMA Rainier 2015** | Et0, Etc, Temperatura, Humedad Relativa, Lluvia, Radiación Solar, Velocidad Viento, Dirección Viento, Presión, Horas frío, Grados día |
| **EMA Santina 2020** | Et0, Etc, Temperatura, Humedad Relativa, Pluviometría, Radiación Solar, Velocidad Viento, Dirección Viento, Presión Atmosférica, Ráfaga Viento, Horas frío, Grados día |

> El Et0 de Zuñiga se calcula como **promedio de ambas EMAs**.

---

### Sectores EQ1 — Ciruelos Adultos

Los 3 sectores EQ1 riegan el mismo cuartel (CC-860) y comparten el **mismo sensor Ubibot** (Z-Ciruelos `#88253`).

| Sector | Cuartel | Wiseconn (11 sensores) | Ubibot: Z-Ciruelos `#88253` |
|--------|---------|------------------------|------------------------------|
| Sector 1 EQ 1 (Dag) | CIRUELOS ADULTOS CC-860 | Caudalimetro EQ1, Etc, Falla Nivel EQ1, Fertigation Time/Volume, Irrigation Precipitation/Time/Volume, Presión EQ1/2/3 | Temperature, Humidity, Humedad suelo 25/50cm, Temperatura suelo 25/50cm, RS485 Soil Moisture, RS485 Soil Temperature, RS485 Humidity, RS485 Temperature, Light, Voltage |
| Sector 2 EQ 1 (Dag) | CIRUELOS ADULTOS CC-860 | _(idéntico al anterior)_ | _(mismo sensor)_ |
| Sector 3 EQ 1 (Dag) | CIRUELOS ADULTOS CC-860 | _(idéntico al anterior)_ | _(mismo sensor)_ |

---

### Sectores EQ2 — Cerezos 2014–2018

| Sector | Cuartel | Wiseconn (11 sensores) | Ubibot |
|--------|---------|------------------------|--------|
| **Sector 1 EQ 2 (San14)** | CEREZOS SANTINA 2014 CC-883 | Caudalimetro EQ2, Etc, Falla Nivel EQ2, Fertigation Time/Volume, Irrigation Precipitation/Time/Volume, Presión EQ1/2/3 | **Z-Santina 2014** `#83204` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 Soil Moisture/Temperature/Humidity/Temperature, Light, Voltage |
| **Sector 2 EQ 2 (Lap14)** | CEREZOS LAPINS 2014 CC-881 | _(idéntico)_ | **3 sensores en distintas posiciones del cuartel:**<br>`#88424` Z-Lapins 2014 — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, Light, Voltage<br>`#88733` Z-Lapins 2014 — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, CO₂, Wind Speed, PT100 Temperature, Presión atmosférica, Light, Voltage<br>`#88736` Z-Lapins 2014 — Temperature, Humidity, Humedad suelo 50cm, Temperatura suelo 25/50cm, CO₂, Wind Speed, PT100 Temperature, Presión atmosférica, Light, Voltage |
| **Sector 3 EQ 2 (Rai15)** | CEREZOS LAPINS 2015 CC-884 | _(idéntico)_ | **Z-Rainier 2015** `#83605` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 Soil Moisture/Temperature/Humidity/Temperature, Light, Voltage |
| **Sector 3 EQ 2 (Rai15)** | CEREZOS RAINIER 2015 CC-882 | _(comparte sector y sensor con Lapins 2015)_ | **Z-Rainier 2015** `#83605` _(mismo sensor)_ |
| **Sector 4 EQ 2 (San18)** | CEREZOS SANTINA 2018 CC-895 | _(idéntico)_ | **Z-Santina 2018** `#88257` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 Soil Moisture/Temperature/Humidity/Temperature, CO₂, Light, Voltage |

---

### Sectores EQ3 — Cerezos 2019–2020

| Sector | Cuartel | Wiseconn (11-12 sensores) | Ubibot |
|--------|---------|---------------------------|--------|
| **Sector 1 EQ 3 (San19s)** | CEREZOS SANTINA 2019 CC-892 | Caudalimetro EQ3, Etc, Falla Nivel EQ3, Fertigation Time/Volume, Irrigation Precipitation/Time/Volume, Presión EQ1/2/3 | **Z-Santina 2019-Sector 1** `#80646` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, CO₂, CO2 Probe Temperature, Light, Voltage + sensores temporales de ensayo (H°/T° plástico jun) |
| **Sector 2 EQ 3 (San19n)** | CEREZOS SANTINA 2019 CC-892 | _(idéntico)_ | **2 sensores:**<br>`#87975` Z-Santina 2019 Sector 2 — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 Soil Moisture/Temperature, Light, Voltage + sensores testigo de ensayo<br>`#88732` Z-Santina norte 2019 — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, CO₂, Wind Speed, PT100 Temperature, RS485 completo, Presión atmosférica, Voltage |
| **Sector 3 EQ 3 (Lap19)** | CEREZOS LAPINS 2019 CC-891 | _(idéntico)_ | _(sin sensor Ubibot — pendiente confirmar)_ |
| **Sector 4 EQ 3 (San20s)** | CEREZOS SANTINA 2020 CC-899 | _(idéntico)_ | **2 sensores:**<br>`#88260` Z-Santina 2020-Sector 4 — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 completo, Light, Voltage<br>`#88738` Z-Santina 2020 Sector 4 — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, CO₂, Wind Speed, PT100 Temperature, Presión atmosférica, Light, Voltage |
| **Sector 5 EQ 3 (San20n)** | CEREZOS SANTINA 2020 CC-899 | _(idéntico)_ | **Z-Santina 2020 Sector 5** `#88261` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 completo, Light, Voltage |

### Sector especial

| Sector | Cuartel | Wiseconn | Ubibot |
|--------|---------|----------|--------|
| **Sector 4 EQ 1 (Cer 24)** | CEREZOS GLOW | Caudalimetro EQ1, Etc, Falla Nivel EQ1, Fertigation Time/Volume, Irrigation Precipitation/Time/Volume, Presión EQ1/2/3 | _(sin sensor Ubibot — pendiente confirmar)_ |

---

## Isla de Maipo — Mapa completo de sensores

### EMA (estación meteorológica)

| EMA | Sensores climáticos |
|-----|---------------------|
| **EMA Isla de Maipo** | Et0, Etc, Temperatura, Humedad Relativa, Lluvia, Radiación Solar, Velocidad Viento, Dirección Viento, Presión, Horas frío, Grados día |

---

### Sectores EQ1 — Cerezos y Ciruelas 2023

| Sector | Cuartel | Wiseconn (8 sensores) | Ubibot |
|--------|---------|----------------------|--------|
| **S1 EQ1 (Tul)** | CIRUELAS TULARE CC-450 | Caudalimetro EQ1, Etc, Fertigation Time/Volume, Irrigation Precipitation/Time/Volume, Volumen Acumulado EQ1 | _(sin sensor Ubibot — pendiente confirmar)_ |
| **S2 EQ1 (Glow)** | CEREZOS GLOW 2023 CC-426 | _(idéntico)_ | **I-1.2 Glow** `#88813` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, CO₂, Wind Speed, PT100 Temperature, Presión atmosférica, Light, Voltage |
| **S3 EQ1** | CEREZOS SANTINA 2023 CC-424 | _(idéntico)_ | **I-1.3 Santina** `#88816` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 completo, CO₂, Wind Speed, PT100 Temperature, Presión atmosférica, Light, Voltage |
| **S4 EQ1** | CEREZOS RAINIER 2023 CC-431 | _(idéntico)_ | **I-1.4 Rainier** `#88737` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 completo, CO₂, Wind Speed, PT100 Temperature, Presión atmosférica, Light, Voltage |

### Sectores EQ2 — Cerezos y Ciruelas

| Sector | Cuartel | Wiseconn (8-9 sensores) | Ubibot |
|--------|---------|------------------------|--------|
| **S1 EQ2** | CEREZOS RED PACIFIC CC-421 | Caudalimetro EQ1/EQ2, Etc, Fertigation Time/Volume, Irrigation Precipitation/Time/Volume, Volumen Acumulado EQ2 | **I-2.3 Pacific B** `#88811` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, RS485 Soil Moisture/Temperature, CO₂, Wind Speed, PT100 Temperature, Presión atmosférica, Light, Voltage |
| **S2 EQ2** | CEREZOS SWEET ARYANA 2023 CC-422 | Caudalimetro EQ2, Etc, Fertigation Time/Volume, Irrigation Precipitation/Time/Volume, Volumen Acumulado EQ2 | **I-2.2 Aryana A** `#88252` — Temperature, Humidity, Humedad/Temperatura suelo 25/50cm, Light, Voltage |
| **S3 EQ2** | CEREZOS RED PACIFIC CC-421 | _(idéntico a S1 EQ2)_ | **I-2.3 Pacific B** `#88811` _(comparte sensor con S1 EQ2)_ |
| **S4 EQ2** | CIRUELAS TULARE CC-450 | Caudalimetro EQ1/EQ2, Etc, Fertigation Time/Volume, Irrigation Precipitation/Time/Volume, Volumen Acumulado EQ1/EQ2 | _(sin sensor Ubibot — pendiente confirmar)_ |

---

## Sensores Ubibot sin sector asignado

Estos dispositivos existen en el sistema pero aún no se pudo identificar a qué sector pertenecen. Requieren confirmación del equipo de terreno.

| Canal ID | Nombre | Campo estimado | Sensores disponibles |
|----------|--------|----------------|----------------------|
| `89019` | Z-IVU 115 2018 | Zuñiga | Humedad suelo, Temperatura suelo, RS485 |
| `71208` | Z-Kiwi | Zuñiga | Temperature, Humidity, CO₂, Suelo, EC |
| `88158` | T-Peonias | Isla de Maipo | Temperature, Humidity, RS485 |
| `88155` | T-Peonias Sin Malla | Isla de Maipo | Temperature, Humidity, RS485 |
| `88251` | T-Peonías Ensayo 3 | Isla de Maipo | Temperature, Humidity, Suelo |
| `88259` | T-Pimentónes Macro Tunel | Isla de Maipo | Temperature, Humidity, Suelo |
| `88271` | T-Túnel Peonías Ensayo 1 | Isla de Maipo | Temperature, Humidity, RS485 |
