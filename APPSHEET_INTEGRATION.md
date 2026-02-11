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

**Última actualización**: Febrero 2026
**Estado**: Planificación
