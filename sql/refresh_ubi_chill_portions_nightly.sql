-- Dynamic-model chill portions rewrite every channel for the current year.
-- That takes about 30 minutes and stalls the shared Cloud SQL instance.
-- The hourly Ubibot sync used to call this on every run. Keep the work in
-- the night window (02:00–06:59 America/Santiago) and at most once per 18 hours.
-- The dedicated job refresh_chill_portions.py is scheduled at 03:00.

CREATE TABLE IF NOT EXISTS public.pipeline_refresh_log (
    job_name TEXT PRIMARY KEY,
    refreshed_at TIMESTAMPTZ NOT NULL
);

CREATE OR REPLACE FUNCTION public.refresh_ubi_chill_portions()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_refresh_from DATE := CURRENT_DATE - INTERVAL '2 days';
    v_current_year TEXT := EXTRACT(YEAR FROM CURRENT_DATE)::TEXT;
    v_local timestamp := timezone('America/Santiago', clock_timestamp());
    r RECORD;
BEGIN
    IF v_local::time < TIME '02:00' OR v_local::time >= TIME '07:00' THEN
        RAISE LOG 'refresh_ubi_chill_portions skipped outside 02:00-07:00 America/Santiago (%)', v_local;
        RETURN;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.pipeline_refresh_log
        WHERE job_name = 'ubi_chill_portions'
          AND refreshed_at > clock_timestamp() - INTERVAL '18 hours'
    ) THEN
        RAISE LOG 'refresh_ubi_chill_portions skipped; last run is within 18 hours';
        RETURN;
    END IF;

    IF NOT pg_try_advisory_xact_lock(hashtext('refresh_ubi_chill_portions')::bigint) THEN
        RAISE LOG 'refresh_ubi_chill_portions skipped; another run holds the lock';
        RETURN;
    END IF;

    -- ----------------------------------------------------------------
    -- 1. Sincronizar metadata + temperatura desde ubi_chill_hours
    -- ----------------------------------------------------------------
    INSERT INTO ubi_chill_portions (
        channel_id, channel_name, field_sector_id,
        field, irrigation_sector, orchard, crop_type,
        date, hour, temperature, dm_season
    )
    SELECT
        channel_id, channel_name, field_sector_id,
        field, irrigation_sector, orchard, crop_type,
        date, hour, temperature,
        EXTRACT(YEAR FROM date)::TEXT AS dm_season
    FROM ubi_chill_hours
    WHERE date >= v_refresh_from
    ON CONFLICT (channel_id, field_sector_id, date, hour) DO UPDATE SET
        temperature       = EXCLUDED.temperature,
        channel_name      = EXCLUDED.channel_name,
        irrigation_sector = EXCLUDED.irrigation_sector;

    -- ----------------------------------------------------------------
    -- 2. Recalcular DM para el año calendario actual completo
    --    Join por (channel_id, field_sector_id, date, hour)
    -- ----------------------------------------------------------------
    FOR r IN
        SELECT DISTINCT channel_id, field_sector_id
        FROM ubi_chill_portions
        WHERE dm_season = v_current_year
        ORDER BY channel_id, field_sector_id
    LOOP
        UPDATE ubi_chill_portions cp
        SET
            dm_state       = dm.dm_state_out,
            dm_value       = dm.dm_value_out,
            dm_accumulated = dm.dm_accumulated_out
        FROM calc_dm_portions(r.channel_id, r.field_sector_id, v_current_year) dm
        WHERE cp.channel_id      = r.channel_id
          AND cp.field_sector_id = r.field_sector_id
          AND cp.date            = dm.date_out
          AND cp.hour            = dm.hour_out;
    END LOOP;

    INSERT INTO public.pipeline_refresh_log (job_name, refreshed_at)
    VALUES ('ubi_chill_portions', clock_timestamp())
    ON CONFLICT (job_name) DO UPDATE
        SET refreshed_at = EXCLUDED.refreshed_at;
END;
$function$
