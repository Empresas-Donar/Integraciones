# Integración AppSheet → Base de Datos SQL

Configurar disparadores en AppSheet que inserten datos automáticamente en PostgreSQL cuando hay cambios, habilitando reportes SQL sin limitaciones de Google Sheets.

## Objetivo

Configurar **disparadores (triggers) en AppSheet** que inserten datos automáticamente en PostgreSQL cuando se crean o modifican registros, permitiendo:
- Inserción automática en tiempo real
- Reportes SQL complejos
- Análisis histórico y comparativo
- Integración con otras fuentes (Wiseconn, Ubibot)

### Visión General del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPSHEET (29 Apps)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Usuario crea/modifica registro                                  │
│           │                                                       │
│           ▼                                                       │
│  ┌──────────────────────┐                                        │
│  │ Disparador (Trigger)  │  AppSheet Automation                   │
│  │ - On Row Add          │  o Webhook                              │
│  │ - On Row Update      │                                        │
│  └──────────┬───────────┘                                        │
│             │                                                     │
│             │ HTTP POST (Webhook)                                 │
│             │                                                     │
└─────────────┼─────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API REST (Cloud Run)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────┐                                        │
│  │ Endpoint:             │  /api/appsheet/webhook                 │
│  │ - Valida datos        │                                        │
│  │ - Normaliza           │                                        │
│  │ - Inserta en BD       │                                        │
│  └──────────┬───────────┘                                        │
│             │                                                     │
└─────────────┼─────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│              POSTGRESQL (CLOUD SQL)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Schema: appsheet                                                 │
│  ├── Tabla 1: contratistas_talagante                             │
│  ├── Tabla 2: epp_talagante                                     │
│  └── Tabla N: ...                                                │
│                                                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CONSUMO                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ Reportes SQL │  │ BI Tools  │  │ REST API │                 │
│  └──────────────┘  └──────────┘  └──────────┘                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Inventario de Apps

### Contratistas
1. Contratistas Talagante
2. Contratistas Kontrolag
3. Contratistas Zúñiga
4. Contratistas Isla de Maipo

### EPP (Equipos de Protección Personal)
5. EPP Talagante
6. EPP_LasVertientes
7. EPP_Zuniga

### Combustible
8. C. Combustible Zuñiga
9. Carga Combustible Talagante
10. C. Combustible Las vertientes

### Cosecha
11. Cosecha
12. Cosecha-Isla de Maipo
13. Cosecha -anterior
14. Trabajadores Cosecha FB

### Registros y Trámites
15. Registro de Trámites
16. Registro Maquinaria-Zuñiga

### Conteos y Mediciones
17. Conteo de Bunching
18. CONTEO DE DARDOS-CEREZOS
19. Medición Pozos

### Plagas y Calicatas
20. Talagante Plagas
21. Calicatas Zúñiga
22. Calicatas Talagante
23. Calicatas Isla de Maipo

### Estado Fenológico
24. Estado Fenológico-Zúñiga
25. Estado Fenológico-I. de Maipo

### Otros
26. DESPACHOS
27. SAG FB
28. Servicios FB
29. Riego

**Total: 29 aplicaciones identificadas**

---

## Opción de Integración

### AppSheet Automation + Webhook → API REST → PostgreSQL

**Flujo:**
1. **AppSheet Automation**: Configurar disparador (trigger) en cada app que se active cuando:
   - Se crea un nuevo registro (`On Row Add`)
   - Se modifica un registro (`On Row Update`)
   
2. **Webhook HTTP POST**: El disparador envía datos a un endpoint REST:
   - URL: `https://api-tu-proyecto.run.app/api/appsheet/webhook`
   - Método: POST
   - Payload: Datos del registro (JSON)
   - Headers: Token de autenticación

3. **API REST (Cloud Run)**: Endpoint que recibe el webhook:
   - Valida autenticación
   - Normaliza datos
   - Inserta/actualiza en PostgreSQL
   - Retorna confirmación

4. **PostgreSQL**: Almacenamiento directo en schema `appsheet`

**Ventajas:**
- ✅ Inserción en tiempo real (no polling)
- ✅ Datos siempre actualizados
- ✅ No requiere extracción programada
- ✅ Escalable (cada app dispara independientemente)
- ✅ Manejo de errores por registro

**Configuración requerida:**
- API REST endpoint en Cloud Run
- Token de autenticación compartido
- Configurar Automation en cada app de AppSheet

---

## Arquitectura

### Diagrama de Flujo General

```
┌─────────────────────────────────────────────────────────────────────┐
│                            APPSHEET                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Usuario crea/modifica registro en App                              │
│           │                                                           │
│           ▼                                                           │
│  ┌──────────────────────────────────────┐                            │
│  │ AppSheet Automation (Trigger)       │                            │
│  │ - On Row Add                        │                            │
│  │ - On Row Update                     │                            │
│  └──────────┬───────────────────────────┘                            │
│             │                                                         │
│             │ HTTP POST (Webhook)                                     │
│             │ Headers: Authorization Token                            │
│             │ Body: JSON con datos del registro                      │
│             │                                                         │
│  ┌──────────┴───────────────────────────┐                            │
│  │ App 1: Contratistas                  │                            │
│  │ App 2: EPP                            │                            │
│  │ App 3: Cosecha                        │                            │
│  │ App N: ...                            │                            │
│  └──────────┬───────────────────────────┘                            │
│             │                                                         │
└─────────────┼─────────────────────────────────────────────────────────┘
              │
              │ POST https://api.run.app/api/appsheet/webhook
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API REST (Cloud Run)                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────┐                            │
│  │ Endpoint: /api/appsheet/webhook      │                            │
│  │                                      │                            │
│  │ 1. Valida token de autenticación    │                            │
│  │ 2. Identifica app y tabla            │                            │
│  │ 3. Normaliza datos                   │                            │
│  │ 4. Valida referencias (catálogos)    │                            │
│  │ 5. Inserta/actualiza en PostgreSQL  │                            │
│  │ 6. Retorna confirmación              │                            │
│  └──────────┬───────────────────────────┘                            │
│             │                                                         │
└─────────────┼─────────────────────────────────────────────────────────┘
              │
              │ SQL INSERT/UPDATE
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  POSTGRESQL (CLOUD SQL)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Schema: appsheet                                                    │
│  ├── Tabla 1: contratistas_talagante                                │
│  ├── Tabla 2: epp_talagante                                         │
│  ├── Tabla 3: cosecha                                                │
│  └── Tabla N: ...                                                    │
│                                                                       │
└─────────────────────────┬─────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         REPORTES                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐          ┌──────────────┐                         │
│  │ BI Tools     │          │ SQL Queries  │                         │
│  └──────────────┘          └──────────────┘                         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Componentes:**
- **Disparador**: AppSheet Automation (configurado en cada app)
- **API REST**: Cloud Run Service (endpoint webhook)
- **Base de Datos**: Cloud SQL PostgreSQL (schema `appsheet`)
- **Secrets**: Secret Manager (token de autenticación)

---

## Diseño de Base de Datos

### Schema: `appsheet`

Cada app tendrá su tabla en el schema `appsheet`:

```sql
CREATE SCHEMA IF NOT EXISTS appsheet;

CREATE TABLE appsheet.contratistas_talagante (
    id SERIAL PRIMARY KEY,
    appsheet_row_id TEXT UNIQUE,
    synced_at TIMESTAMP DEFAULT NOW(),
    source_updated_at TIMESTAMP,
    data_hash TEXT,
    -- Campos específicos de la app
    ...
);
```

**Nomenclatura**: `{app_name_snake_case}` (ej: `contratistas_talagante`, `epp_talagante`)

### Apps con Múltiples Tablas

Muchas apps AppSheet tienen múltiples tablas, incluyendo:
- **Tablas principales**: Datos transaccionales (ej: registros de contratistas, cosecha)
- **Tablas de catálogo**: Datos de referencia (ej: trabajadores, productos, estados)
- **Tablas de configuración**: Parámetros y configuraciones

#### Estrategia de Disparadores

1. **Configurar Automation en cada tabla** de cada app:
   - **Catálogos**: Disparador `On Row Add` y `On Row Update`
   - **Tablas principales**: Disparador `On Row Add` y `On Row Update`
   
2. **Orden de procesamiento**: Cuando llega un registro de tabla principal:
   - Validar que las referencias (catálogos) existan en PostgreSQL
   - Si no existen, insertar primero el catálogo referenciado
   - Luego insertar/actualizar el registro principal

3. **Manejo de relaciones**: Validar referencias por `appsheet_row_id` antes de insertar

#### Estructura de Tablas por App

Cada app con múltiples tablas tendrá varias tablas en PostgreSQL:

```sql
-- Ejemplo: App "Contratistas Talagante" con múltiples tablas

-- Catálogo: Trabajadores
CREATE TABLE appsheet.contratistas_talagante_trabajadores (
    id SERIAL PRIMARY KEY,
    appsheet_row_id TEXT UNIQUE,
    synced_at TIMESTAMP DEFAULT NOW(),
    nombre TEXT,
    rut TEXT,
    cargo TEXT,
    activo BOOLEAN
);

-- Catálogo: Tipos de Trabajo
CREATE TABLE appsheet.contratistas_talagante_tipos_trabajo (
    id SERIAL PRIMARY KEY,
    appsheet_row_id TEXT UNIQUE,
    synced_at TIMESTAMP DEFAULT NOW(),
    codigo TEXT UNIQUE,
    nombre TEXT,
    descripcion TEXT
);

-- Tabla Principal: Registros de Contratistas
CREATE TABLE appsheet.contratistas_talagante_registros (
    id SERIAL PRIMARY KEY,
    appsheet_row_id TEXT UNIQUE,
    synced_at TIMESTAMP DEFAULT NOW(),
    source_updated_at TIMESTAMP,
    data_hash TEXT,
    fecha DATE,
    trabajador_appsheet_id TEXT,  -- ID de AppSheet, no FK estricta
    tipo_trabajo_appsheet_id TEXT, -- ID de AppSheet, no FK estricta
    horas DECIMAL(5,2),
    monto DECIMAL(10,2),
    observaciones TEXT
);

-- Índices para performance en joins (opcional, si se necesita)
CREATE INDEX idx_registros_trabajador ON appsheet.contratistas_talagante_registros(trabajador_appsheet_id);
CREATE INDEX idx_registros_tipo_trabajo ON appsheet.contratistas_talagante_registros(tipo_trabajo_appsheet_id);
```

#### Configuración para Apps Multi-Tabla

En `config/appsheet_sources.yaml`:

```yaml
apps:
  - name: "Contratistas Talagante"
    app_id: "abc123xyz"
    webhook_url: "https://api.run.app/api/appsheet/webhook"
    webhook_token: "token-secreto"
    tables:
      # Catálogos (sincronizar primero)
      - name: "trabajadores"
        type: "catalog"
        sync_order: 1
        primary_key: ["rut"]
        table_name: "contratistas_talagante_trabajadores"
        
      - name: "tipos_trabajo"
        type: "catalog"
        sync_order: 2
        primary_key: ["codigo"]
        table_name: "contratistas_talagante_tipos_trabajo"
        
      # Tabla principal (sincronizar después)
      - name: "registros"
        type: "main"
        sync_order: 3
        primary_key: ["appsheet_row_id"]  # Usar ID de AppSheet como PK
        table_name: "contratistas_talagante_registros"
        references:  # Referencias por ID, no FKs estrictas
          - column: "trabajador_appsheet_id"
            references_table: "contratistas_talagante_trabajadores"
            references_column: "appsheet_row_id"
          - column: "tipo_trabajo_appsheet_id"
            references_table: "contratistas_talagante_tipos_trabajo"
            references_column: "appsheet_row_id"
```

#### Manejo de Referencias en Tiempo Real

Cuando llega un registro de tabla principal con referencias a catálogos:

1. **Validar referencias**: Verificar si los `appsheet_row_id` de catálogos existen en PostgreSQL
2. **Insertar catálogos faltantes**: Si una referencia no existe:
   - Opción A: Rechazar el registro y retornar error (requiere que catálogos se inserten primero)
   - Opción B: Insertar automáticamente el catálogo referenciado (si los datos vienen en el payload)
3. **Insertar registro principal**: Una vez validadas/creadas las referencias, insertar el registro

**Estrategia Recomendada:**
- **Catálogos**: Deben insertarse primero (configurar Automation antes que tablas principales)
- **Validación**: Si referencia no existe, retornar error 400 con mensaje claro
- **Idempotencia**: Usar `appsheet_row_id` como clave única para evitar duplicados

### Diagrama de Flujo de Disparador (Trigger)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USUARIO EN APPSHEET                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Usuario crea o modifica registro                                   │
│           │                                                           │
│           ▼                                                           │
│  ┌──────────────────────────────────────┐                            │
│  │ AppSheet Automation                  │                            │
│  │ Trigger: On Row Add / On Row Update │                            │
│  └──────────┬───────────────────────────┘                            │
│             │                                                         │
│             │ Detecta cambio                                          │
│             │                                                         │
└─────────────┼─────────────────────────────────────────────────────────┘
              │
              │ Construye payload JSON
              │ {
              │   "app_name": "Contratistas Talagante",
              │   "table_name": "registros",
              │   "action": "add" | "update",
              │   "data": { ... },
              │   "appsheet_row_id": "..."
              │ }
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HTTP POST REQUEST                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  POST https://api.run.app/api/appsheet/webhook                       │
│  Headers:                                                            │
│    - Authorization: Bearer <token>                                    │
│    - Content-Type: application/json                                │
│  Body: JSON payload                                                  │
│                                                                       │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API REST (CLOUD RUN)                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────┐                          │
│  │ 1. Validar Token                     │                          │
│  └───────────┬──────────────────────────┘                          │
│              │                                                       │
│              ▼                                                       │
│  ┌──────────────────────────────────────┐                          │
│  │ 2. Identificar App y Tabla           │                          │
│  │    (buscar en config YAML)          │                          │
│  └───────────┬──────────────────────────┘                          │
│              │                                                       │
│              ▼                                                       │
│  ┌──────────────────────────────────────┐                          │
│  │ 3. Validar Referencias               │                          │
│  │    (si es tabla principal, verificar │                          │
│  │     que catálogos existan)           │                          │
│  └───────────┬──────────────────────────┘                          │
│              │                                                       │
│              ▼                                                       │
│  ┌──────────────────────────────────────┐                          │
│  │ 4. Normalizar Datos                  │                          │
│  │    - Agregar campos de control       │                          │
│  │    - Calcular hash                   │                          │
│  └───────────┬──────────────────────────┘                          │
│              │                                                       │
│              ▼                                                       │
│  ┌──────────────────────────────────────┐                          │
│  │ 5. Insertar/Actualizar PostgreSQL   │                          │
│  │    INSERT ... ON CONFLICT DO UPDATE  │                          │
│  └───────────┬──────────────────────────┘                          │
│              │                                                       │
│              ▼                                                       │
│  ┌──────────────────────────────────────┐                          │
│  │ 6. Retornar Respuesta                │                          │
│  │    { "status": "success",            │                          │
│  │      "id": 123 }                     │                          │
│  └───────────┬──────────────────────────┘                          │
│              │                                                       │
└──────────────┼───────────────────────────────────────────────────────┘
               │
               │ HTTP 200 OK
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL (CLOUD SQL)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Registro insertado/actualizado en:                                  │
│  appsheet.contratistas_talagante_registros                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Estrategia de Disparadores:**
- Cada cambio en AppSheet dispara automáticamente inserción en PostgreSQL
- No requiere polling ni sincronización programada
- Validación de referencias en tiempo real antes de insertar
- Manejo de errores por registro (si falla uno, no afecta otros)

#### Manejo de Relaciones

**Opción A: Referencias por ID de AppSheet (Recomendada) ✅**
- Guardar `appsheet_row_id` o IDs originales como texto
- Más flexible durante sincronización (no falla si catálogo no está sincronizado)
- Permite sincronización parcial sin errores de integridad
- Alineado con patrón del código existente (Wiseconn/Ubibot usan IDs, no FKs estrictas)

**Opción B: Foreign Keys Estrictas**
- Mantener integridad referencial en BD
- Validar relaciones al insertar
- ⚠️ Requiere sincronizar catálogos primero (si falla catálogo, falla todo)
- ⚠️ Más rígido para sincronización incremental

**Recomendación Validada**: 
- **Usar Referencias por ID** (Opción A) para mayor flexibilidad
- Mantener `appsheet_row_id` en todas las tablas para trazabilidad
- Opcionalmente agregar índices en campos de referencia para performance en queries
- Las relaciones se validan en la lógica de aplicación, no en la BD

#### Casos Especiales

**Catálogos compartidos entre apps:**
- Si múltiples apps usan el mismo catálogo (ej: "Trabajadores"), crear tabla compartida:
  ```sql
  CREATE TABLE appsheet.catalogos_trabajadores (...);
  ```
- Referenciar desde múltiples apps

**Catálogos que cambian raramente:**
- Sincronizar con menor frecuencia (ej: diaria en vez de horaria)
- Configurar `sync_frequency: "daily"` en el YAML

**Tablas de historial:**
- Si la app mantiene historial de cambios, sincronizar tabla de historial por separado
- Considerar si mantener solo estado actual o historial completo

### Diagrama de Relaciones entre Tablas

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CATALOGO_TRABAJADORES                           │
├─────────────────────────────────────────────────────────────────────┤
│  PK: id (SERIAL)                                                    │
│  UK: appsheet_row_id (TEXT)                                         │
│                                                                      │
│  Campos:                                                            │
│    - synced_at (TIMESTAMP)                                          │
│    - nombre (TEXT)                                                  │
│    - rut (TEXT)                                                     │
│    - cargo (TEXT)                                                   │
│                                                                      │
│         │                                                            │
│         │ referencia por appsheet_row_id                             │
│         │ (no FK estricta)                                          │
│         │                                                            │
└─────────┼────────────────────────────────────────────────────────────┘
          │
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        REGISTROS                                    │
├─────────────────────────────────────────────────────────────────────┤
│  PK: id (SERIAL)                                                    │
│  UK: appsheet_row_id (TEXT)                                         │
│                                                                      │
│  Campos:                                                            │
│    - synced_at (TIMESTAMP)                                          │
│    - fecha (DATE)                                                   │
│    - trabajador_appsheet_id (TEXT)  ────┐                          │
│    - tipo_trabajo_appsheet_id (TEXT) ───┼───┐                      │
│    - horas (DECIMAL)                    │   │                      │
│    - monto (DECIMAL)                    │   │                      │
│                                          │   │                      │
│  NOTA: Relaciones por appsheet_row_id   │   │                      │
│        No FKs estrictas en BD           │   │                      │
│        Validación en lógica de app      │   │                      │
└─────────────────────────────────────────┼───┼──────────────────────┘
                                          │   │
                                          │   │ referencia por
                                          │   │ appsheet_row_id
                                          │   │ (no FK estricta)
                                          │   │
┌─────────────────────────────────────────┘   │
│                    CATALOGO_TIPOS_TRABAJO    │
├──────────────────────────────────────────────┤
│  PK: id (SERIAL)                             │
│  UK: appsheet_row_id (TEXT)                  │
│                                               │
│  Campos:                                     │
│    - synced_at (TIMESTAMP)                   │
│    - codigo (TEXT)                           │
│    - nombre (TEXT)                           │
│                                               │
└──────────────────────────────────────────────┘
```

---

## Plan de Implementación

### Fase 1: Configuración
- [ ] Crear `config/appsheet_sources.yaml` con inventario de apps y tablas
- [ ] Identificar todas las tablas por app (principales y catálogos)
- [ ] Mapear relaciones entre tablas
- [ ] Crear schema `appsheet` en PostgreSQL
- [ ] Generar token de autenticación para webhooks

### Fase 2: Desarrollo API REST
- [ ] Crear endpoint webhook (`app/routes/appsheet_webhook.py`)
  - Validar token de autenticación
  - Identificar app y tabla desde payload
  - Validar referencias a catálogos
  - Normalizar datos
- [ ] Persistencia PostgreSQL (`app/services/appsheet_database.py`)
  - Usar patrón similar a `database.py`
  - Implementar `INSERT ... ON CONFLICT DO UPDATE` con `appsheet_row_id`
- [ ] Manejo de referencias por ID (validar catálogos antes de insertar)
- [ ] Manejo de errores y respuestas HTTP apropiadas

### Fase 3: Despliegue
- [ ] Desplegar API REST en Cloud Run
- [ ] Configurar dominio y HTTPS
- [ ] Configurar Secret Manager (token de autenticación)
- [ ] Logging estructurado (JSON)

### Fase 4: Configuración en AppSheet
- [ ] Configurar Automation en cada app (empezar con catálogos)
- [ ] Configurar disparadores `On Row Add` y `On Row Update`
- [ ] Configurar webhook URL y token en cada Automation
- [ ] Probar con 1-2 apps de prueba

### Fase 5: Rollout
- [ ] Validar datos insertados correctamente
- [ ] Expandir a todas las apps
- [ ] Monitorear logs y errores

---

## Configuración

### Variables de Entorno (Secret Manager)
- `APPSHEET_WEBHOOK_TOKEN`: Token de autenticación para validar webhooks
- `APPSHEET_CONFIG_PATH`: Ruta al YAML de configuración
- `DATABASE_URL`: URL de conexión a PostgreSQL (ya existe)

### Archivo de Configuración

`config/appsheet_sources.yaml`:
```yaml
webhook:
  url: "https://api-tu-proyecto.run.app/api/appsheet/webhook"
  token: "${APPSHEET_WEBHOOK_TOKEN}"  # Desde Secret Manager

apps:
  - name: "Contratistas Talagante"
    app_id: "abc123xyz"
    tables:
      - name: "trabajadores"
        type: "catalog"
        table_name: "contratistas_talagante_trabajadores"
        primary_key: ["appsheet_row_id"]
        
      - name: "registros"
        type: "main"
        table_name: "contratistas_talagante_registros"
        primary_key: ["appsheet_row_id"]
        references:
          - column: "trabajador_appsheet_id"
            references_table: "contratistas_talagante_trabajadores"
            references_column: "appsheet_row_id"
  # ... más apps
```

---

## Consideraciones Técnicas

### Rate Limiting
- **AppSheet Automation**: Límites dependen del plan (típicamente 100-1000 requests/día)
- **API REST**: Cloud Run puede manejar múltiples requests concurrentes
- **Estrategia**: Implementar rate limiting en el endpoint si es necesario
- **Manejo de picos**: Cloud Run escala automáticamente

### Idempotencia
- Usar `INSERT ... ON CONFLICT (appsheet_row_id) DO UPDATE` en PostgreSQL
- Clave única: `appsheet_row_id` (ID de fila en AppSheet)
- Si llega el mismo registro dos veces, se actualiza en vez de duplicar
- Alineado con patrón del código existente (ver `database.py`)

### Manejo de Errores
- **Errores de validación**: Retornar HTTP 400 con mensaje descriptivo
- **Errores de BD**: Retornar HTTP 500, loggear error
- **Referencias faltantes**: Retornar HTTP 400 indicando qué catálogo falta
- **Timeouts**: Cloud Run tiene timeout de 60 min (suficiente para inserts simples)

### Validación de Referencias
- Cuando llega registro de tabla principal, validar que catálogos referenciados existan
- Consultar PostgreSQL por `appsheet_row_id` antes de insertar
- Si referencia no existe, retornar error 400 con mensaje claro
- Recomendación: Configurar Automation de catálogos antes que tablas principales

### Relaciones
- **No usar Foreign Keys estrictas** (más flexible)
- Guardar `appsheet_row_id` de referencias como texto
- Validar relaciones en lógica de aplicación antes de insertar
- Crear índices en campos de referencia para performance en validación

### Catálogos Compartidos
- Identificar catálogos comunes entre apps (ej: "Trabajadores")
- Considerar tabla compartida `appsheet.catalogos_*` si múltiples apps lo usan
- Mismo webhook puede manejar múltiples apps que usan el mismo catálogo

### Performance
- Cada request inserta un registro (no batch necesario)
- Usar transacciones simples (INSERT/UPDATE)
- Índices en `appsheet_row_id` para búsquedas rápidas
- Cloud Run escala automáticamente según carga

---

## Estructura de Código

```
app/
├── routes/
│   └── appsheet_webhook.py  # Endpoint webhook (/api/appsheet/webhook)
├── services/
│   └── appsheet_database.py # Persistencia PostgreSQL
└── __init__.py              # Flask app factory

config/
└── appsheet_sources.yaml    # Configuración de apps y tablas

main.py                       # Entry point (Cloud Run)
```

---

## Próximos Pasos

1. **Desarrollo API REST**: Crear endpoint webhook en Cloud Run
2. **Configuración**: Crear YAML con inventario completo de apps y tablas
3. **Despliegue**: Desplegar API REST y obtener URL pública
4. **Configuración AppSheet**: Configurar Automation en cada app (empezar con catálogos)
5. **Testing**: Probar con 1-2 apps de prueba
6. **Rollout**: Expandir Automation a todas las apps

---

## Referencias

- [AppSheet Automation](https://help.appsheet.com/en/articles/automation)
- [AppSheet Webhooks](https://help.appsheet.com/en/articles/webhooks)
- [Cloud Run Services](https://cloud.google.com/run/docs/create-services)
- [Flask REST API](https://flask.palletsprojects.com/)

---

## Validación de Estrategia

### ✅ Estrategia Validada

La estrategia propuesta ha sido validada contra:
- **AppSheet Automation**: Soporta disparadores (triggers) que pueden llamar webhooks HTTP
- **Google Cloud Best Practices**: Cloud Run es ideal para APIs REST con escalado automático
- **Código Existente**: Alineado con patrones de `database.py` para persistencia
- **Mejores Prácticas**: Inserción en tiempo real, validación de referencias, idempotencia

### ⚠️ Consideraciones Importantes

1. **Configuración en AppSheet**: Cada app necesita Automation configurado manualmente
2. **Orden de Configuración**: Configurar Automation de catálogos antes que tablas principales
3. **Validación de Referencias**: Validar que catálogos existan antes de insertar registros principales
4. **Manejo de Errores**: Retornar errores claros para debugging en AppSheet

### 📋 Decisiones Pendientes

- [ ] Definir formato exacto del payload JSON que enviará AppSheet
- [ ] Identificar catálogos compartidos entre apps
- [ ] Decidir estrategia si referencia a catálogo no existe (error vs insertar automáticamente)
- [ ] Configurar token de autenticación y almacenarlo en Secret Manager
- [ ] Definir estrategia de historial (solo actual vs histórico completo)

---

**Última actualización**: Febrero 2026  
**Estado**: Planificación - Validado
