"""Fix wc_zones_sensors duplicates, add unique constraint, fix refresh_wc_kc_daily Et0

Revision ID: a1b2c3d4e5f6
Revises: 551111690c71
Create Date: 2026-04-08

Problema: el pipeline hourly insertaba duplicados en wc_zones_sensors porque la clave
de dedup usaba created_at (timestamp), pero la API entrega sensores diarios con
time=00:00:00 y cada run traía el dato con un timestamp ligeramente diferente.
Resultado: hasta 24 filas por sensor por día, distorsionando el Et0 en wc_kc_daily.

Fixes aplicados:
1. Elimina filas duplicadas (conserva la más reciente por date+sensor_id+zone_id)
2. Agrega UNIQUE constraint en (date, sensor_id, zone_id) para evitar futuros duplicados
3. Corrige refresh_wc_kc_daily: usa MAX(et0) en lugar de AVG para el Et0 diario
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '551111690c71'
branch_labels = None
depends_on = None


def upgrade():
    # ----------------------------------------------------------------
    # 1. Eliminar duplicados: conservar la fila con id más alto
    #    (el último insert) por cada combinación (date, sensor_id, zone_id)
    # ----------------------------------------------------------------
    op.execute("""
        DELETE FROM wc_zones_sensors
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM wc_zones_sensors
            GROUP BY date, sensor_id, zone_id
        )
    """)

    # ----------------------------------------------------------------
    # 2. Agregar UNIQUE constraint para prevenir futuros duplicados
    # ----------------------------------------------------------------
    op.create_unique_constraint(
        'uq_wc_zones_sensors_date_sensor_zone',
        'wc_zones_sensors',
        ['date', 'sensor_id', 'zone_id']
    )

    # ----------------------------------------------------------------
    # 3. Corregir refresh_wc_kc_daily:
    #    - Usar MAX(et0) por día en lugar de AVG (el acumulado diario es el valor del día)
    #    - GROUP BY date + field (no por sector individual) para el CTE de Et0
    # ----------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION public.refresh_wc_kc_daily()
        RETURNS void
        LANGUAGE sql
        AS $function$
            INSERT INTO wc_kc_daily (date, field, irrigation_sector, orchard, crop_type, field_sector_id, irrigated_mm, et0_mm, kc)
            WITH et0_per_field AS (
                -- MAX por zona EMA (valor acumulado del día), luego AVG entre las zonas del predio
                -- Esto es correcto para Zuñiga (2 EMAs) e Isla de Maipo (1 EMA)
                SELECT
                    date,
                    field,
                    AVG(zone_et0) AS et0_mm
                FROM (
                    SELECT
                        s.date,
                        z.farm_id,
                        fs_field.field,
                        s.zone_id,
                        MAX(s."values") AS zone_et0
                    FROM wc_zones_sensors s
                    JOIN wc_farms_zones z       ON z.id = CAST(CAST(s.zone_id AS float) AS integer)
                    JOIN field_sectors fs_field ON fs_field.farm_id = z.farm_id
                    WHERE s.name = 'Et0'
                      AND z.farm_id IN (14245, 60544)
                      AND s.date >= CURRENT_DATE - INTERVAL '2 days'
                    GROUP BY s.date, z.farm_id, fs_field.field, s.zone_id
                ) per_zone
                GROUP BY date, field
            ),
            irrigated_per_sector AS (
                SELECT
                    r.date,
                    fs.id AS field_sector_id,
                    fs.field,
                    fs.irrigation_sector,
                    fs.orchard,
                    fs.crop_type,
                    SUM(r.precipitation_mm) AS irrigated_mm
                FROM wc_farms_realirrigation r
                JOIN field_sectors fs ON fs.wc_zone_id = r.zone_id
                WHERE r.date >= CURRENT_DATE - INTERVAL '2 days'
                GROUP BY r.date, fs.id, fs.field, fs.irrigation_sector, fs.orchard, fs.crop_type
            )
            SELECT
                i.date,
                i.field,
                i.irrigation_sector,
                i.orchard,
                i.crop_type,
                i.field_sector_id,
                ROUND(i.irrigated_mm::numeric, 2)                          AS irrigated_mm,
                ROUND(e.et0_mm::numeric, 2)                                AS et0_mm,
                ROUND((i.irrigated_mm / NULLIF(e.et0_mm, 0))::numeric, 2) AS kc
            FROM irrigated_per_sector i
            JOIN et0_per_field e ON e.field = i.field AND e.date = i.date
            ON CONFLICT (date, field, irrigation_sector, orchard) DO UPDATE SET
                crop_type       = EXCLUDED.crop_type,
                field_sector_id = EXCLUDED.field_sector_id,
                irrigated_mm    = EXCLUDED.irrigated_mm,
                et0_mm          = EXCLUDED.et0_mm,
                kc              = EXCLUDED.kc;
        $function$
    """)


def downgrade():
    # Revertir la función al estado anterior (AVG simple)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.refresh_wc_kc_daily()
        RETURNS void
        LANGUAGE sql
        AS $function$
            INSERT INTO wc_kc_daily (date, field, irrigation_sector, orchard, crop_type, field_sector_id, irrigated_mm, et0_mm, kc)
            WITH et0_per_field AS (
                SELECT
                    s.date,
                    fs_field.field,
                    AVG(s."values") AS et0_mm
                FROM wc_zones_sensors s
                JOIN wc_farms_zones z       ON z.id = CAST(CAST(s.zone_id AS float) AS integer)
                JOIN field_sectors fs_field ON fs_field.farm_id = z.farm_id
                WHERE s.name = 'Et0'
                  AND z.farm_id IN (14245, 60544)
                  AND s.date >= CURRENT_DATE - INTERVAL '2 days'
                GROUP BY s.date, fs_field.field
            ),
            irrigated_per_sector AS (
                SELECT
                    r.date,
                    fs.id AS field_sector_id,
                    fs.field,
                    fs.irrigation_sector,
                    fs.orchard,
                    fs.crop_type,
                    SUM(r.precipitation_mm) AS irrigated_mm
                FROM wc_farms_realirrigation r
                JOIN field_sectors fs ON fs.wc_zone_id = r.zone_id
                WHERE r.date >= CURRENT_DATE - INTERVAL '2 days'
                GROUP BY r.date, fs.id, fs.field, fs.irrigation_sector, fs.orchard, fs.crop_type
            )
            SELECT
                i.date,
                i.field,
                i.irrigation_sector,
                i.orchard,
                i.crop_type,
                i.field_sector_id,
                ROUND(i.irrigated_mm::numeric, 2)                          AS irrigated_mm,
                ROUND(e.et0_mm::numeric, 2)                                AS et0_mm,
                ROUND((i.irrigated_mm / NULLIF(e.et0_mm, 0))::numeric, 2) AS kc
            FROM irrigated_per_sector i
            JOIN et0_per_field e ON e.field = i.field AND e.date = i.date
            ON CONFLICT (date, field, irrigation_sector, orchard) DO UPDATE SET
                crop_type       = EXCLUDED.crop_type,
                field_sector_id = EXCLUDED.field_sector_id,
                irrigated_mm    = EXCLUDED.irrigated_mm,
                et0_mm          = EXCLUDED.et0_mm,
                kc              = EXCLUDED.kc;
        $function$
    """)

    op.drop_constraint(
        'uq_wc_zones_sensors_date_sensor_zone',
        'wc_zones_sensors',
        type_='unique'
    )
