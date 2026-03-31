# Integración AppSheet con PostgreSQL (Cloud SQL)

Conectar las aplicaciones AppSheet directamente a Cloud SQL PostgreSQL como datasource nativo, habilitando lectura y escritura sin intermediarios.

## Objetivo

Migrar las apps AppSheet desde Google Sheets a **PostgreSQL (Cloud SQL)** como fuente de datos directa, permitiendo:
- Lectura y escritura nativa desde AppSheet
- Reportes SQL sin limitaciones de Sheets
- Análisis cruzado con datos de Wiseconn y Ubibot
- Mayor rendimiento y escalabilidad
- Integridad de datos y concurrencia

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPSHEET (40 Apps)                            │
│                                                                  │
│  Lectura y escritura directa sobre PostgreSQL                   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Tarjas   │  │Despachos │  │ Cosecha  │  │  EPP     │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │             │
└───────┼──────────────┼──────────────┼──────────────┼─────────────┘
        │              │              │              │
        └──────────────┴──────┬───────┴──────────────┘
                              │
                              │ Cloud SQL Connector
                              │ (lectura + escritura)
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  POSTGRESQL (Cloud SQL)                          │
│                                                                  │
│  Schema: appsheet                                                │
│  ├── tarjas_zuniga                                               │
│  ├── tarjas_talagante                                            │
│  ├── despachos                                                   │
│  ├── cosecha                                                     │
│  └── ... (40 apps)                                               │
│                                                                  │
│  Schema: public (existente)                                      │
│  ├── wc_farms_zones         (Wiseconn)                           │
│  ├── ubi_channel_data       (Ubibot)                             │
│  └── execution_log                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CONSUMO                                  │
│                                                                  │
│  ┌──────────────┐  ┌──────────┐  ┌───────────────────┐         │
│  │ Reportes SQL │  │ BI Tools │  │ Consultas cruzadas│         │
│  └──────────────┘  └──────────┘  └───────────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Componentes:**
- **AppSheet**: Apps conectadas directamente a Cloud SQL como datasource
- **Cloud SQL PostgreSQL**: Base de datos centralizada (schema `appsheet`)
- **Cloud SQL Connector**: Conexión nativa de AppSheet a Cloud SQL via Google Cloud

---

## Inventario de Apps (40 aplicaciones)

### 1. Operaciones de Terreno y Producción

| # | App | Descripción |
|---|-----|-------------|
| 1 | Tarjas Zúñiga | Registro de producción individual de trabajadores para pagos por trato y jornada |
| 2 | Tarjas Talagante | Registro de producción individual de trabajadores para pagos por trato y jornada |
| 3 | Tarjas Isla de Maipo | Registro de producción individual de trabajadores para pagos por trato y jornada |
| 4 | Tarjas Kontrolag | Registro de producción individual de trabajadores para pagos por trato y jornada |
| 5 | Despachos | Registro de pesajes de despachos para emisión de guías |
| 6 | Conteo de Bunching | Contabilización de muestreos de plantas para análisis estadístico |
| 7 | Cosecha | Registro de capachos en cerezas y ciruelas, logística de bins y cálculo de pagos semanales |
| 8 | Cosecha Isla de Maipo | Registro de capachos, logística de bins y cálculo de pagos semanales |
| 9 | Conteo de Dardos Cerezas | Registro de dardos florales para estimar potencial productivo de la temporada |
| 10 | Conteo de Dardos Ciruelas | Registro de dardos florales para estimar potencial productivo de la temporada |
| 11 | Trabajadores FB | Registro de trabajos, gastos y consumos del personal de maquinaria de cosecha para liquidaciones |
| 12 | Cosecha Pimentón Ensayo | Registro de cosecha de pimentón experimental |
| 13 | Control de Calidad en Packing | Evaluación de calibre, color y defectos en la línea de proceso |

### 2. Maquinaria y Recursos Operativos

| # | App | Descripción |
|---|-----|-------------|
| 14 | Consumos de Combustibles Zúñiga | Control de carga de combustible a equipos y vehículos para asignación de costos |
| 15 | Consumos de Combustibles Isla de Maipo | Control de carga de combustible a equipos y vehículos para asignación de costos |
| 16 | Consumos de Combustibles Talagante | Control de carga de combustible a equipos y vehículos para asignación de costos |
| 17 | Registro de Maquinarias Zúñiga | Bitácora de uso (horómetros, labores e implementos) para gestión de mantenciones y costos |
| 18 | Registro de Maquinarias Talagante | Bitácora de uso (horómetros, labores e implementos) para gestión de mantenciones y costos |
| 19 | Registro de Maquinarias Isla de Maipo | Bitácora de uso (horómetros, labores e implementos) para gestión de mantenciones y costos |
| 20 | Inventario FB | Gestión de stock de repuestos y asignación al personal |
| 21 | Herramientas | Gestión de stock de herramientas prestadas al personal |
| 22 | Medición Pozos | Registro de mediciones de niveles de pozos |

### 3. Control Técnico y Agronómico

| # | App | Descripción |
|---|-----|-------------|
| 23 | Monitoreo de Plagas Isla de Maipo | Registro de presencia de plagas y enfermedades para historiales fitosanitarios |
| 24 | Monitoreo de Plagas Zúñiga | Registro de presencia de plagas y enfermedades para historiales fitosanitarios |
| 25 | Monitoreo de Plagas Talagante | Registro de presencia de plagas y enfermedades para historiales fitosanitarios |
| 26 | Calicatas Zúñiga | Análisis de perfiles de suelo para evaluar la humedad |
| 27 | Calicatas Isla de Maipo | Análisis de perfiles de suelo para evaluar la humedad |
| 28 | Calicatas Talagante | Análisis de perfiles de suelo para evaluar la humedad |
| 29 | Riego | Registro de eventos de riego (sectores, tiempos y caudales) para control hídrico |
| 30 | Estados Fenológicos Zúñiga | Monitoreo del desarrollo de las plantas para programar labores agronómicas |
| 31 | Estados Fenológicos Isla de Maipo | Monitoreo del desarrollo de las plantas para programar labores agronómicas |
| 32 | Asesorías Técnicas Zúñiga | Centralización de recomendaciones y tareas de asesores durante visitas |
| 33 | Asesorías Técnicas Talagante | Centralización de recomendaciones y tareas de asesores durante visitas |
| 34 | Asesorías Técnicas Isla de Maipo | Centralización de recomendaciones y tareas de asesores durante visitas |

### 4. Administración y Logística

| # | App | Descripción |
|---|-----|-------------|
| 35 | Trámites | Registro de trámites bancarios, compras y traslados realizados por choferes |
| 36 | Control de EPP Talagante | Control de entrega y devolución de equipos de protección personal |
| 37 | Control de EPP Servicios FB | Control de entrega y devolución de equipos de protección personal |
| 38 | EPP Las Vertientes | Control de entrega y devolución de equipos de protección personal |
| 39 | EPP Zúñiga | Control de entrega y devolución de equipos de protección personal |
| 40 | SAG FB | Registros relacionados con el Servicio Agrícola y Ganadero |

**Total: 40 aplicaciones**

---

## Configuración de Cloud SQL como Datasource

### Requisitos Previos

1. **Cloud SQL PostgreSQL** activo en Google Cloud (ya existente)
2. **IP pública** o **Private Service Connect** habilitado en la instancia Cloud SQL
3. **Usuario de base de datos** dedicado para AppSheet (con permisos de lectura/escritura en schema `appsheet`)

### Paso 1: Preparar la Base de Datos

```sql
-- Crear schema dedicado para apps AppSheet
CREATE SCHEMA IF NOT EXISTS appsheet;

-- Crear usuario dedicado para AppSheet (permisos limitados)
CREATE USER appsheet_user WITH PASSWORD 'password_seguro';
GRANT USAGE ON SCHEMA appsheet TO appsheet_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA appsheet TO appsheet_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA appsheet GRANT ALL ON TABLES TO appsheet_user;
```

### Paso 2: Conectar AppSheet a Cloud SQL

1. En AppSheet, ir a **Data > + New Data Source**
2. Seleccionar **Cloud SQL** (disponible en planes Business+)
3. Configurar la conexión:
   - **Project**: ID del proyecto de Google Cloud
   - **Instance**: Nombre de la instancia Cloud SQL
   - **Database**: Nombre de la base de datos
   - **Schema**: `appsheet`
   - **User/Password**: Credenciales del usuario dedicado

### Paso 3: Crear Tablas

Para cada app, crear las tablas necesarias en el schema `appsheet`. AppSheet leerá la estructura de las tablas automáticamente.

Cada tabla debe tener como mínimo:
- `id` (SERIAL PRIMARY KEY) - Clave primaria autogenerada
- Campos específicos de la app

### Paso 4: Configurar la App en AppSheet

1. Agregar las tablas del schema `appsheet` como datasource
2. Configurar columnas, tipos de datos y validaciones en AppSheet
3. Configurar vistas, formularios y workflows

---

## Convenciones

### Nomenclatura de Tablas

```
appsheet.{app_name_snake_case}
```

Ejemplos:
- `appsheet.tarjas_zuniga`
- `appsheet.despachos`
- `appsheet.cosecha`
- `appsheet.epp_talagante`
- `appsheet.combustibles_zuniga`
- `appsheet.monitoreo_plagas_zuniga`

### Apps con Múltiples Tablas

Si una app tiene múltiples tablas (principal + catálogos), usar sufijo:

```
appsheet.{app_name}_{tabla}
```

Ejemplo para "Cosecha":
- `appsheet.cosecha_registros` (tabla principal)
- `appsheet.cosecha_trabajadores` (catálogo)
- `appsheet.cosecha_variedades` (catálogo)

---

## Consideraciones

### Seguridad
- Usar un usuario de BD dedicado para AppSheet con permisos solo en schema `appsheet`
- No dar acceso al schema `public` (donde están datos de Wiseconn/Ubibot)
- Credenciales gestionadas via Secret Manager

### Rendimiento
- Cloud SQL soporta múltiples conexiones concurrentes
- Agregar índices en columnas usadas frecuentemente en filtros de AppSheet
- Monitorear conexiones activas desde la consola de Cloud SQL

### Migración desde Google Sheets
- Exportar datos existentes de Sheets a CSV
- Importar CSV a las tablas PostgreSQL correspondientes
- Cambiar datasource en AppSheet de Sheets a Cloud SQL
- Validar que la app funcione correctamente con el nuevo datasource

### Reportes SQL Cruzados

Con todos los datos en PostgreSQL, se pueden hacer consultas cruzadas:

```sql
-- Ejemplo: Cruzar datos de riego (AppSheet) con sensores (Wiseconn)
SELECT
    r.sector,
    r.fecha,
    r.caudal,
    s.values as sensor_value
FROM appsheet.riego r
JOIN public.wc_zones_sensors s ON r.sector = s.zone_id
WHERE r.fecha = CURRENT_DATE;
```

---

## Plan de Implementación

### Fase 1: Infraestructura
- [ ] Crear schema `appsheet` en Cloud SQL
- [ ] Crear usuario dedicado `appsheet_user` con permisos apropiados
- [ ] Verificar conectividad de AppSheet a Cloud SQL

### Fase 2: App Piloto
- [ ] Seleccionar 1-2 apps simples para migrar primero (ej: EPP, Trámites)
- [ ] Crear tablas en PostgreSQL
- [ ] Conectar AppSheet a Cloud SQL
- [ ] Validar lectura y escritura
- [ ] Migrar datos históricos desde Google Sheets

### Fase 3: Rollout por Categoría
- [ ] Migrar apps de Administración y Logística (6 apps)
- [ ] Migrar apps de Maquinaria y Recursos Operativos (9 apps)
- [ ] Migrar apps de Control Técnico y Agronómico (12 apps)
- [ ] Migrar apps de Operaciones de Terreno y Producción (13 apps)

### Fase 4: Reportes
- [ ] Crear queries SQL para reportes cruzados
- [ ] Conectar herramientas de BI si es necesario

---

## Infraestructura Existente

| Componente | Servicio | Región |
|-----------|---------|--------|
| Base de Datos | Cloud SQL PostgreSQL | southamerica-west1 (Santiago) |
| Jobs (Wiseconn/Ubibot) | Cloud Run Jobs | southamerica-west1 |
| Secrets | Secret Manager | Global |
| Scheduler | Cloud Scheduler | southamerica-east1 |

---

---

## App: Tarjas

### Descripción

App de registro y liquidación de trabajadores de contratistas. Permite ingresar jornadas, tratos y horas extra diarias por trabajador, y calcula automáticamente los montos a pagar al trabajador y al contratista.

### Tablas (schema `appsheet`, prefijo `tarjas_`)

| Tabla | Rol |
|-------|-----|
| `tarjas_campo` | Catálogo de predios |
| `tarjas_cc` | Centros de costo (cuarteles) con cultivo y campo |
| `tarjas_contratistas` | Contratistas con tasas de pago y porcentajes |
| `tarjas_personal` | Trabajadores vinculados a un contratista |
| `tarjas_labor` | Labores con valores diferenciados por operador y día |
| `tarjas_labores` | (variante de labores — uso a confirmar) |
| `tarjas_trato` | Tratos activos con valor, base y fechas de vigencia |
| `tarjas_jornada` | Tipos de jornada (horas) por campo |
| `tarjas_supervisor` | Supervisores |
| `tarjas_maquina` | Maquinaria disponible |
| `tarjas_plan_diario` | Planificación diaria de labores |
| `tarjas_usuarios` | Usuarios de la app con roles |
| `tarjas_pagos` | **Liquidación final** — 1 fila por trabajador por día |

### Flujo de datos hacia `tarjas_pagos`

```
[Catálogos]
  tarjas_campo        → nombre del predio
  tarjas_cc           → cultivo, id_campo
  tarjas_contratistas → porcentaje_jornada, porcentaje_trato, valor_hora_extra
  tarjas_personal     → rut, nombre del trabajador
  tarjas_labor        → valores de jornada según operador y día
  tarjas_trato        → valor y base del trato vigente

[Ingreso diario — origen en AppSheet]
  El supervisor ingresa en la app:
    - Contratista, campo, CC, labor, fecha
    - Trabajador(es), tipo de pago (jornada / trato)
    - Para jornada: fracción de jornada + horas extra
    - Para trato: rendimiento (unidades) + base

[Liquidación final]
  tarjas_pagos → AppSheet calcula y escribe 1 fila por trabajador por día
```

`tarjas_pagos` NO es una vista SQL — AppSheet la calcula con fórmulas virtuales y la escribe directamente en PostgreSQL.

### Tabla: `tarjas_pagos`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_Resumen` | text | ID único del registro de pago |
| `id_supervisor` | text | FK → `tarjas_contratistas.id_contratista` |
| `fecha` | text | Fecha del registro |
| `nombre_campo` | text | FK → `tarjas_campo.nombre` |
| `cuartel_cc` | integer | FK → `tarjas_cc.id_cc` |
| `labor` | text | FK → `tarjas_labor.id_labor` |
| `contratista` | text | Nombre del contratista |
| `trabajador` | text | Nombre del trabajador |
| `rut_trabajador` | text | RUT del trabajador |
| `tipo_pago` | text | `jornada` o `trato` |
| `valor_jornada` | integer | Valor base de jornada ($) — de `tarjas_labor` |
| `valor_trato` | integer | Valor por unidad de trato ($) — de `tarjas_trato.valor` |
| `base_trato` | integer | Base de cálculo del trato — de `tarjas_trato.base` |
| `rendimiento` | text | Unidades producidas (tratos) |
| `horas_extras` | text | Horas extra trabajadas |
| `maquina` | text | FK → `tarjas_maquina` (si aplica) |
| `total_tractor` | integer | Pago adicional por uso de maquinaria |
| `horas_trabajadas` | text | Horas efectivas trabajadas |
| `total_hora_extra` | text | Monto por horas extra ($) |
| `total_jornada` | integer | Monto por jornada ($) |
| `total_trato` | integer | Monto por trato (`rendimiento × valor_trato`) |
| `total_trabajado` | integer | Subtotal trabajador (`total_jornada + total_trato + total_hora_extra`) |
| `contratista_jornada` | integer | Margen contratista sobre jornada (`total_jornada × porcentaje_jornada`) |
| `contratista_trato` | integer | Margen contratista sobre trato (`total_trato × porcentaje_trato`) |
| `total_contratista` | integer | Total a pagar al contratista |
| `total_pagar` | integer | **Total general** (`total_trabajado + total_contratista`) |
| `estado` | text | Estado del pago (`Al día`, `A trato`, etc.) |

### Lógica de cálculo de montos (fórmulas AppSheet)

| Campo calculado | Fórmula (lógica) |
|-----------------|-----------------|
| `valor_jornada` | lookup de `tarjas_labor` según labor y tipo de día |
| `valor_trato` | `tarjas_trato.valor` del trato vigente |
| `total_hora_extra` | `horas_extras × tarjas_contratistas.valor_hora_extra` |
| `total_jornada` | fracción de jornada × `valor_jornada` |
| `total_trato` | `rendimiento × valor_trato` |
| `total_trabajado` | `total_jornada + total_trato + total_hora_extra + total_tractor` |
| `contratista_jornada` | `total_jornada × tarjas_contratistas.porcentaje_jornada` |
| `contratista_trato` | `total_trato × tarjas_contratistas.porcentaje_trato` |
| `total_contratista` | `contratista_jornada + contratista_trato` |
| `total_pagar` | `total_trabajado + total_contratista` |

> **Nota**: Las fórmulas exactas viven en AppSheet. Los valores en `tarjas_pagos` son el resultado ya calculado.

### Relaciones clave

```
tarjas_pagos.id_supervisor  →  tarjas_contratistas.id_contratista
tarjas_pagos.cuartel_cc     →  tarjas_cc.id_cc
tarjas_pagos.labor          →  tarjas_labor.id_labor
tarjas_pagos.nombre_campo   →  tarjas_campo.nombre
tarjas_pagos.rut_trabajador →  tarjas_personal.rut
```

---

### Vista de reporte: `appsheet.tarjas_reporte`

Agrupa `tarjas_pagos` por **día** (`fecha`). Looker Studio aplica sus propios filtros de rango de fechas encima, por lo que sirve tanto para reportes diarios como semanales sin necesitar vistas adicionales.

| Columna | Descripción |
|---------|-------------|
| `contratista` | Nombre del contratista |
| `nombre_campo` | Predio |
| `fecha` | Fecha del registro |
| `total_a_trato` | Total pagado a trato ese día ($) |
| `total_al_dia` | Total pagado al día ese día ($) |
| `total_a_pagar` | Total general (`total_a_trato + total_al_dia`) |
| `pct_trato` | % del total que corresponde a trato |
| `pct_al_dia` | % del total que corresponde a jornada |
| `tipo_pago` | `trato` o `Al dia` |
| `CC` | Centro de costo (cuartel) |
| `Nombre Labor` | Nombre de la labor |
| `jornadas` | Cantidad de trabajadores en esa labor+CC ese día |
| `total_unitario` | Promedio pagado por trabajador en esa labor ($) |
| `total_labor` | Total pagado en esa labor+CC ese día ($) |
| `% Tipo de pago` | % que representa esa labor sobre el total del día |

**Ejemplo — reporte por rango de fechas (27 feb al 26 mar 2026, MARCELA YANETT ORELLANA ALLENDES):**

```sql
SELECT
    contratista,
    nombre_campo,
    fecha,
    total_a_trato,
    total_al_dia,
    total_a_pagar,
    pct_trato,
    pct_al_dia,
    tipo_pago,
    "CC",
    "Nombre Labor",
    jornadas,
    total_unitario,
    total_labor,
    "% Tipo de pago"
FROM appsheet.tarjas_reporte
WHERE fecha BETWEEN '2026-02-27' AND '2026-03-26'
  AND contratista = 'MARCELA YANETT ORELLANA ALLENDES'
ORDER BY fecha, tipo_pago, "CC";
```

Resultado:

| fecha | total_a_trato | total_al_dia | total_a_pagar | pct_trato | pct_al_dia | tipo_pago | CC | Nombre Labor | jornadas | total_unitario | total_labor | % Tipo de pago |
|-------|--------------|-------------|--------------|-----------|-----------|-----------|-----|--------------|----------|---------------|------------|---------------|
| 2026-02-27 | 221.000 | 215.400 | 436.400 | 50,6 | 49,4 | Al dia | 422 | INCISIÓN | 6 | 15.000 | 90.000 | 20,62 |
| 2026-02-27 | 221.000 | 215.400 | 436.400 | 50,6 | 49,4 | Al dia | 431 | INCISIÓN | 7 | 17.914 | 125.400 | 28,74 |
| 2026-02-27 | 221.000 | 215.400 | 436.400 | 50,6 | 49,4 | trato | 420 | DESYEME | 6 | 36.833 | 221.000 | 50,64 |
| 2026-03-02 | 0 | 9.800 | 9.800 | 0,0 | 100,0 | Al dia | 420 | PASAR RANA | 1 | 9.800 | 9.800 | 100,00 |
| 2026-03-19 | 0 | 34.200 | 34.200 | 0,0 | 100,0 | Al dia | 420 | PASAR RANA | 8 | 4.275 | 34.200 | 100,00 |
| 2026-03-22 | 12.100 | 0 | 12.100 | 100,0 | 0,0 | trato | 420 | [2.1]AMARRA | 2 | 6.050 | 12.100 | 100,00 |
| 2026-03-26 | 5.300 | 37.000 | 42.300 | 12,5 | 87,5 | Al dia | 424 | ACARREO COSECHA | 2 | 18.500 | 37.000 | 87,47 |
| 2026-03-26 | 5.300 | 37.000 | 42.300 | 12,5 | 87,5 | trato | 421 | [2.1]AMARRA | 1 | 5.300 | 5.300 | 12,53 |

> **Nota de lectura**: `total_a_trato`, `total_al_dia` y `total_a_pagar` son **totales del día completo** — se repiten en cada fila de detalle del mismo día. Las filas de detalle desglosan por `tipo_pago + CC + labor`. En Looker Studio, estos totales van en la cabecera del reporte y el detalle se muestra en la tabla inferior.

---

### Vista de importación a Odoo: `appsheet.tarjas_reporte_odoo`

Genera el archivo de líneas de pedido que se importa a Odoo, mapeando cada labor a su `product_id` y cada fila a las columnas `order_line/*` que Odoo espera.

**Fuentes:**

| Tabla | Aporte |
|-------|--------|
| `tarjas_reporte` | Datos de pago: contratista, labor, jornadas, precio unitario |
| `tarjas_labores` | Código de producto Odoo (`codigo_labor`) por nombre de labor |
| `tarjas_cc` | Nombre del cultivo asociado al CC (referencia para `analytic_distribution`) |

**Columnas de la vista:**

| Columna vista | Campo Odoo | Descripción |
|---------------|-----------|-------------|
| `Vendedor` | `partner_id` | Nombre del contratista |
| `Lineas del pedido/Producto/Nombre` | — | Nombre de la labor |
| `Lineas del pedido/Cantidad` | `order_line/product_qty` | Jornadas (cantidad de trabajadores) |
| `CC` | — | Centro de costo (cuartel) |
| `order_line/product_id` | `order_line/product_id` | Código de labor de `tarjas_labores` (ej. `3.5`, `2.1`) |
| `cc_cultivo` | referencia | Nombre del cultivo del CC — guía para asignar `analytic_distribution` en Odoo |
| `Lineas del pedido/Precio un.` | `order_line/price_unit` | Precio promedio por trabajador ($) |

**Lógica de resolución de `order_line/product_id`:**

1. Join directo por nombre exacto: `tarjas_labores.labor = "Nombre Labor"` (ej. `ACARREO COSECHA` → `12.7`)
2. Si el nombre tiene prefijo `[X.Y]` (ej. `[2.1]AMARRA`), extrae el código `2.1` y lo busca en `tarjas_labores.codigo_labor`

Labores sin `product_id` (sin match en `tarjas_labores`): `Hora Extra`, `Jornada Tractor` — no generan línea de pedido en Odoo.

**Query de ejemplo — semana 25–30 marzo 2026:**

```sql
SELECT
    "Vendedor",
    "Lineas del pedido/Producto/Nombre",
    "Lineas del pedido/Cantidad",
    "CC",
    "order_line/product_id",
    "cc_cultivo",
    "Lineas del pedido/Precio un.",
    "partner_id",
    "order_line/product_qty",
    "order_line/price_unit"
FROM appsheet.tarjas_reporte_odoo
WHERE fecha BETWEEN '2026-03-25' AND '2026-03-30'
ORDER BY "Vendedor", "CC";
```

> **`analytic_distribution`**: En el reporte de Sheets original se resuelve con un BUSCARV sobre una hoja "Cultivos" que mapea `CC → JSON de distribución analítica`. Este JSON vive en Odoo, no en PostgreSQL. Por ahora la vista expone `cc_cultivo` como referencia; si se migra la tabla de distribuciones analíticas a PostgreSQL se puede incorporar directamente.

---

**Última actualización**: Febrero 2026
**Estado**: Planificación
