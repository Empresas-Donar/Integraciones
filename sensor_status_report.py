import os
import argparse
import logging
from datetime import date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.mail_class import MailManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ACTIVE_THRESHOLD_DAYS = 2
DEGRADED_THRESHOLD_DAYS = 7


def classify(rows, id_key, name_key, farm_key=None):
    active, degraded, down = [], [], []
    for row in rows:
        row = dict(row._mapping)
        days = row["days_since"] if row["days_since"] is not None else 9999
        entry = {
            "id": row[id_key],
            "name": row[name_key],
            "last_reading": row["last_reading"],
            "days_since": days,
            "field": row.get("field"),
        }
        if days <= ACTIVE_THRESHOLD_DAYS:
            active.append(entry)
        elif days <= DEGRADED_THRESHOLD_DAYS:
            degraded.append(entry)
        else:
            down.append(entry)
    return active, degraded, down


def get_ubibot_status(session):
    rows = session.execute(text("""
        SELECT
            cd.channel_id,
            cd.name,
            MAX(ucf.date)                AS last_reading,
            CURRENT_DATE - MAX(ucf.date) AS days_since
        FROM ubi_channel_data cd
        LEFT JOIN ubi_channels_fields ucf ON cd.channel_id = ucf.channel_id
        GROUP BY cd.channel_id, cd.name
        ORDER BY days_since DESC NULLS FIRST
    """)).fetchall()
    return classify(rows, "channel_id", "name")


def get_daily_summary(session, date_from, date_to):
    rows = session.execute(text("""
        SELECT
            ucf.date,
            COUNT(DISTINCT ucf.channel_id) AS ubi_canales,
            ROUND(AVG(ucf.avg) FILTER (WHERE ucf.name = 'Temperature')::numeric, 1) AS temp_avg,
            (SELECT COUNT(DISTINCT CAST(NULLIF(ws.zone_id,'NaN') AS numeric)::integer)
             FROM wc_zones_sensors ws WHERE ws.date = ucf.date) AS wc_zonas,
            EXISTS(SELECT 1 FROM wc_farms_realirrigation r
                   WHERE r.date = ucf.date AND r.farm_id = 14245) AS riego_zuniga,
            EXISTS(SELECT 1 FROM wc_farms_realirrigation r
                   WHERE r.date = ucf.date AND r.farm_id = 60544) AS riego_isla
        FROM ubi_channels_fields ucf
        WHERE ucf.date BETWEEN :date_from AND :date_to
        GROUP BY ucf.date
        ORDER BY ucf.date
    """), {"date_from": date_from, "date_to": date_to}).fetchall()
    return [dict(r._mapping) for r in rows]


def get_ubibot_climate_summary(session, date_from, date_to):
    row = session.execute(text("""
        SELECT
            ROUND(AVG(temperature)::numeric, 1) AS temp_avg,
            ROUND(MIN(temperature)::numeric, 1) AS temp_min,
            ROUND(MAX(temperature)::numeric, 1) AS temp_max,
            ROUND(AVG(humidity)::numeric, 1)    AS hum_avg,
            ROUND(AVG(light)::numeric, 0)       AS light_avg
        FROM ubi_sensor_pivot
        WHERE date BETWEEN :date_from AND :date_to
    """), {"date_from": date_from, "date_to": date_to}).fetchone()
    return dict(row._mapping) if row else {}


def get_wiseconn_status(session):
    rows = session.execute(text("""
        SELECT
            wz.id          AS zone_id,
            wz.name,
            CASE wz.farm_id
                WHEN 14245 THEN 'ZUÑIGA'
                WHEN 60544 THEN 'ISLA DE MAIPO'
                ELSE wz.farm_id::text
            END            AS field,
            MAX(ws.date)   AS last_reading,
            CURRENT_DATE - MAX(ws.date) AS days_since
        FROM wc_farms_zones wz
        LEFT JOIN wc_zones_sensors ws
               ON wz.id = CAST(NULLIF(ws.zone_id, 'NaN') AS numeric)::integer
        GROUP BY wz.id, wz.name, wz.farm_id
        ORDER BY days_since DESC NULLS FIRST
    """)).fetchall()
    return classify(rows, "zone_id", "name")


def get_wiseconn_irrigation_summary(session, date_from, date_to):
    rows = session.execute(text("""
        SELECT
            CASE farm_id
                WHEN 14245 THEN 'ZUÑIGA'
                WHEN 60544 THEN 'ISLA DE MAIPO'
            END                                         AS field,
            ROUND(SUM(precipitation_mm)::numeric, 1)    AS total_mm,
            COUNT(DISTINCT date)                         AS dias_con_riego
        FROM wc_farms_realirrigation
        WHERE date BETWEEN :date_from AND :date_to
        GROUP BY farm_id
        ORDER BY field
    """), {"date_from": date_from, "date_to": date_to}).fetchall()
    return [dict(r._mapping) for r in rows]


def fmt_date(d):
    return d.strftime("%d/%m/%Y") if d else "sin datos"


def section(lines, label, items, id_label, show_field=False):
    lines.append(label)
    for c in items:
        field_str = f" [{c['field']}]" if show_field and c.get("field") else ""
        lines.append(f"  {'❌' if 'CAÍDOS' in label else '⚠️ ' if 'DEGRADADOS' in label else '✅ '} "
                     f"[{c['id']}] {c['name']}{field_str}")
        if "ACTIVOS" not in label:
            lines.append(f"       Última lectura: {fmt_date(c['last_reading'])}  ({c['days_since']} días atrás)")
        else:
            lines.append(f"       Última lectura: {fmt_date(c['last_reading'])}")
    lines.append("")


def day_status(ubi_canales, wc_zonas, ubi_total=25, wc_total=24):
    ubi_ok = ubi_canales >= ubi_total
    wc_ok  = wc_zonas   >= wc_total
    if ubi_ok and wc_ok:
        return "🟢"
    elif wc_zonas == 0 and ubi_canales == 0:
        return "🔴"
    return "🟡"


def build_report(period_label, date_from, date_to, ubi_active, ubi_degraded, ubi_down,
                 wc_active, wc_degraded, wc_down,
                 climate=None, irrigation=None, daily=None):
    lines = []
    lines.append(f"REPORTE {period_label.upper()} DE SENSORES — {date_from.strftime('%d/%m/%Y')} al {date_to.strftime('%d/%m/%Y')}")
    lines.append("=" * 60)
    lines.append("")

    # ── Tabla diaria ────────────────────────────────────────
    if daily:
        lines.append("| Día        | Sistema | Wiseconn      | Ubibot                  | Riego Zuñiga | Riego Isla Maipo |")
        lines.append("|------------|---------|---------------|-------------------------|--------------|-----------------|")
        for d in daily:
            wc_str  = f"{d['wc_zonas']}/24"
            ubi_str = f"{d['ubi_canales']} canales  {d['temp_avg']}°C"
            estado  = day_status(d['ubi_canales'], d['wc_zonas'])
            wc_icon  = "🟢" if d['wc_zonas'] >= 24 else ("🟡" if d['wc_zonas'] > 0 else "🔴")
            ubi_icon = "🟢" if d['ubi_canales'] >= 25 else ("🟡" if d['ubi_canales'] > 0 else "🔴")
            rz = "💧" if d['riego_zuniga'] else "—"
            ri = "💧" if d['riego_isla']   else "—"
            lines.append(f"| {d['date'].strftime('%d/%m/%Y')} | {estado}      | {wc_icon} `{wc_str:<7}` | {ubi_icon} `{ubi_str:<23}` | {rz}            | {ri}               |")
        lines.append("")

    # ── Resumen Ubibot ──────────────────────────────────────
    ubi_total_n = len(ubi_active) + len(ubi_degraded) + len(ubi_down)
    lines.append(f"UBIBOT — {ubi_total_n} canales  |  ✅ {len(ubi_active)} activos  |  ⚠️  {len(ubi_degraded)} degradados  |  ❌ {len(ubi_down)} caídos")
    if climate:
        lines.append(f"Clima período: 🌡 {climate.get('temp_avg')}°C (min {climate.get('temp_min')} / max {climate.get('temp_max')})  💧 Humedad {climate.get('hum_avg')}%  ☀️ Luz {climate.get('light_avg')} lux")
    if ubi_down:
        lines.append("")
        lines.append("Caídos:")
        for c in ubi_down:
            lines.append(f"  ❌ [{c['id']}] {c['name']}  — última lectura: {fmt_date(c['last_reading'])} ({c['days_since']} días)")
    if ubi_degraded:
        lines.append("Degradados:")
        for c in ubi_degraded:
            lines.append(f"  ⚠️  [{c['id']}] {c['name']}  — última lectura: {fmt_date(c['last_reading'])} ({c['days_since']} días)")
    lines.append("")

    # ── Resumen Wiseconn ────────────────────────────────────
    wc_total_n = len(wc_active) + len(wc_degraded) + len(wc_down)
    lines.append(f"WISECONN — {wc_total_n} sectores  |  ✅ {len(wc_active)} activos  |  ⚠️  {len(wc_degraded)} degradados  |  ❌ {len(wc_down)} caídos")
    if irrigation:
        for r in irrigation:
            lines.append(f"Agua {r['field']}: 💧 {r['total_mm']} mm en {r['dias_con_riego']} días")
    if wc_down:
        lines.append("")
        lines.append("Caídos:")
        for c in wc_down:
            lines.append(f"  ❌ [{c['id']}] {c['name']} [{c['field']}]  — última lectura: {fmt_date(c['last_reading'])} ({c['days_since']} días)")
    lines.append("")

    lines.append("─" * 60)
    lines.append("Sistema de Monitoreo — Empresas Donar")
    lines.append("Este reporte se genera automáticamente cada semana y mes.")

    return "\n".join(lines)


def send_report(period):
    DATABASE_URL = os.getenv('DATABASE_URL')
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        today = date.today()
        if period == "weekly":
            period_label = "Semanal"
            # Lunes anterior → domingo (últimos 7 días)
            date_to   = today - timedelta(days=1)          # ayer (domingo)
            date_from = date_to - timedelta(days=6)        # lunes anterior
        else:
            period_label = "Mensual"
            # Día 1 del mes actual → ayer
            date_from = today.replace(day=1)
            date_to   = today - timedelta(days=1)

        ubi_active, ubi_degraded, ubi_down = get_ubibot_status(session)
        wc_active, wc_degraded, wc_down    = get_wiseconn_status(session)
        climate    = get_ubibot_climate_summary(session, date_from, date_to)
        irrigation = get_wiseconn_irrigation_summary(session, date_from, date_to)
        daily      = get_daily_summary(session, date_from, date_to)

        body = build_report(period_label, date_from, date_to,
                            ubi_active, ubi_degraded, ubi_down,
                            wc_active, wc_degraded, wc_down,
                            climate=climate, irrigation=irrigation, daily=daily)

        total_down = len(ubi_down) + len(wc_down)
        total_degraded = len(ubi_degraded) + len(wc_degraded)
        if total_down:
            status_tag = f"⚠️ {total_down} caído(s)"
        elif total_degraded:
            status_tag = f"⚠️ {total_degraded} degradado(s)"
        else:
            status_tag = "✅ Todo OK"

        subject = f"[{status_tag}] Reporte {period_label} de Sensores — {date.today().strftime('%d/%m/%Y')}"

        mail_manager = MailManager()
        mail_manager.send_mail(subject, body)
        logging.info(f"Reporte {period_label} enviado — Ubibot: {len(ubi_active)} activos / {len(ubi_down)} caídos | "
                     f"Wiseconn: {len(wc_active)} activos / {len(wc_down)} caídos")

    except Exception as e:
        logging.error(f"Error generando reporte {period}: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", choices=["weekly", "monthly"], required=True)
    args = parser.parse_args()
    send_report(args.period)
