"""
Generates STATUS.md — a full historical calendar showing daily data health
for Wiseconn and Ubibot across all fields.

Indicators per day:
  🟢  All executions succeeded + data received
  🟡  Partial: some executions failed or fewer sensors than expected
  🔴  Total failure: no data for that day
  ⚪  No executions scheduled (before system start)
"""

import os
import psycopg2
from datetime import date, timedelta
from collections import defaultdict

DB_URL = os.environ["DATABASE_URL"]

# Expected values for health checks
EXPECTED_EXECUTIONS_PER_DAY = 24
# Ubibot: 18 channels assigned in field_sectors but only ~9 report consistently.
# Historical max = 18, average = 11. Thresholds based on real observed activity.
UBIBOT_GREEN_THRESHOLD = 10   # >= 10 channels = healthy
UBIBOT_YELLOW_THRESHOLD = 5   # 5-9 channels = degraded
# below 5 = 🔴
EXPECTED_WC_FARMS = 2         # Zuñiga + Isla de Maipo


def connect():
    return psycopg2.connect(DB_URL)


def fetch_execution_summary(cur):
    cur.execute("""
        SELECT
            date::date AS fecha,
            COUNT(*) AS total,
            SUM(CASE WHEN status_wiseconn = 'Success' THEN 1 ELSE 0 END) AS wc_ok,
            SUM(CASE WHEN status_ubibot   = 'Success' THEN 1 ELSE 0 END) AS ubi_ok
        FROM execution_log
        GROUP BY date::date
        ORDER BY fecha
    """)
    rows = cur.fetchall()
    return {r[0]: {"total": r[1], "wc_ok": r[2], "ubi_ok": r[3]} for r in rows}


def fetch_wc_et0_days(cur):
    """Days where both farms reported Et0 (Wiseconn EMA health)."""
    cur.execute("""
        SELECT date, COUNT(DISTINCT farm_id) AS farms
        FROM wc_zones_sensors
        WHERE name = 'Et0'
        GROUP BY date
    """)
    return {r[0]: r[1] for r in cur.fetchall()}


def fetch_ubibot_channels_per_day(cur):
    """Active Ubibot channels per day — uses ubi_channels_fields which has full history."""
    cur.execute("""
        SELECT date, COUNT(DISTINCT channel_id) AS canales
        FROM ubi_channels_fields
        GROUP BY date
    """)
    return {r[0]: r[1] for r in cur.fetchall()}


def fetch_ubibot_avg_temp_per_day(cur):
    """Average temperature reported by Ubibot sensors per day."""
    cur.execute("""
        SELECT date, ROUND(AVG(avg)::numeric, 1) AS temp_avg
        FROM ubi_channels_fields
        WHERE name = 'Temperature'
        GROUP BY date
    """)
    return {r[0]: float(r[1]) for r in cur.fetchall()}


def fetch_irrigation_days(cur):
    """Days with at least one irrigation event per farm."""
    cur.execute("""
        SELECT r.date, fs.farm_id, COUNT(*) AS eventos
        FROM wc_farms_realirrigation r
        JOIN field_sectors fs ON fs.wc_zone_id = r.zone_id
        GROUP BY r.date, fs.farm_id
    """)
    result = defaultdict(dict)
    for row in cur.fetchall():
        result[row[0]][row[1]] = row[2]
    return result


def status_icon(ok, warning, total_possible=None):
    if ok and not warning:
        return "🟢"
    if warning and not ok:
        return "🔴"
    return "🟡"


def day_status(exec_data, et0_data, ubi_data, d):
    """Compute overall day status: 🟢 🟡 🔴 ⚪"""
    ubi_channels = ubi_data.get(d, 0)

    if d not in exec_data:
        # Pipeline didn't run — check if data exists anyway (backfilled)
        if ubi_channels > 0 or et0_data.get(d, 0) > 0:
            return "🟡"
        return "⚪"

    e = exec_data[d]
    wc_rate = e["wc_ok"] / e["total"] if e["total"] else 0
    ubi_rate = e["ubi_ok"] / e["total"] if e["total"] else 0
    et0_farms = et0_data.get(d, 0)

    all_ok = (
        wc_rate == 1.0
        and ubi_rate == 1.0
        and et0_farms >= EXPECTED_WC_FARMS
        and ubi_channels >= UBIBOT_GREEN_THRESHOLD
    )
    total_fail = wc_rate == 0 and ubi_rate == 0 and ubi_channels == 0

    if total_fail:
        return "🔴"
    if all_ok:
        return "🟢"
    return "🟡"


def build_month_table(year, month, all_days, exec_data, et0_data, ubi_data, irr_data, temp_data):
    from calendar import monthrange
    _, days_in_month = monthrange(year, month)
    month_names = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                   "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    lines = [f"### {month_names[month]} {year}\n"]
    lines.append("| Día | Sistema | Wiseconn | Ubibot | Riego Zuñiga | Riego Isla Maipo |")
    lines.append("|-----|---------|----------|--------|--------------|-----------------|")

    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        if d > date.today():
            break

        overall = day_status(exec_data, et0_data, ubi_data, d)

        # Ubibot (always available — independent of execution_log)
        ubi_ch = ubi_data.get(d, 0)
        temp = temp_data.get(d)
        temp_str = f" `{temp}°C`" if temp is not None else ""

        # Irrigation (always available — based on real event timestamps)
        irr = irr_data.get(d, {})
        zuniga_icon = "💧" if 14245 in irr else "—"
        imaipo_icon = "💧" if 60544 in irr else "—"

        if d not in exec_data:
            # Pipeline didn't run — show data that exists independently
            if ubi_ch >= UBIBOT_GREEN_THRESHOLD:
                ubi_icon = "🟢"
            elif ubi_ch >= UBIBOT_YELLOW_THRESHOLD:
                ubi_icon = "🟡"
            elif ubi_ch > 0:
                ubi_icon = "🔴"
            else:
                ubi_icon = "⚪"
            ubi_str = f"`{ubi_ch} canales`{temp_str}" if ubi_ch > 0 else "⚪"
            lines.append(f"| {day:02d} | {overall} | ⚪ | {ubi_icon} {ubi_str} | {zuniga_icon} | {imaipo_icon} |")
            continue

        e = exec_data[d]
        wc_rate = e["wc_ok"] / e["total"] if e["total"] else 0
        ubi_rate = e["ubi_ok"] / e["total"] if e["total"] else 0

        # Wiseconn status
        et0 = et0_data.get(d, 0)
        if wc_rate == 1.0 and et0 >= EXPECTED_WC_FARMS:
            wc_icon = "🟢"
        elif wc_rate == 0:
            wc_icon = "🔴"
        else:
            wc_icon = "🟡"

        # Ubibot status
        if ubi_rate == 1.0 and ubi_ch >= UBIBOT_GREEN_THRESHOLD:
            ubi_icon = "🟢"
        elif ubi_ch < UBIBOT_YELLOW_THRESHOLD:
            ubi_icon = "🔴"
        else:
            ubi_icon = "🟡"

        lines.append(
            f"| {day:02d} | {overall} | {wc_icon} `{e['wc_ok']}/{e['total']}` "
            f"| {ubi_icon} `{ubi_ch} canales`{temp_str} "
            f"| {zuniga_icon} | {imaipo_icon} |"
        )

    return "\n".join(lines)


def generate_status_md():
    conn = connect()
    cur = conn.cursor()

    exec_data = fetch_execution_summary(cur)
    et0_data = fetch_wc_et0_days(cur)
    ubi_data = fetch_ubibot_channels_per_day(cur)
    irr_data = fetch_irrigation_days(cur)
    temp_data = fetch_ubibot_avg_temp_per_day(cur)

    conn.close()

    start_date = date(2024, 6, 6)   # First execution
    today = date.today()

    # Collect all (year, month) pairs in range
    months = []
    y, m = start_date.year, start_date.month
    while (y, m) <= (today.year, today.month):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1

    lines = [
        "# Estado del Sistema — Historial Completo",
        "",
        f"_Actualizado: {today.strftime('%d/%m/%Y')}_",
        "",
        "## Leyenda",
        "",
        "| Ícono | Significado |",
        "|-------|------------|",
        "| 🟢 | Todo OK |",
        "| 🟡 | Parcial: algunas ejecuciones fallaron o menos sensores de lo esperado |",
        "| 🔴 | Sin datos ese día |",
        "| ⚪ | Sin ejecuciones (antes del sistema) |",
        "| 💧 | Hubo eventos de riego ese día |",
        "| — | Sin riego ese día |",
        "",
        "---",
        "",
    ]

    # Summary stats
    all_days = [(y, m) for y, m in months]
    total_days = (today - start_date).days + 1
    green_days = sum(1 for d_offset in range(total_days)
                     if day_status(exec_data, et0_data, ubi_data,
                                   start_date + timedelta(days=d_offset)) == "🟢")
    yellow_days = sum(1 for d_offset in range(total_days)
                      if day_status(exec_data, et0_data, ubi_data,
                                    start_date + timedelta(days=d_offset)) == "🟡")
    red_days = sum(1 for d_offset in range(total_days)
                   if day_status(exec_data, et0_data, ubi_data,
                                 start_date + timedelta(days=d_offset)) == "🔴")

    lines += [
        "## Resumen general",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Período | {start_date.strftime('%d/%m/%Y')} → {today.strftime('%d/%m/%Y')} |",
        f"| Días totales | {total_days} |",
        f"| 🟢 Días OK | {green_days} ({green_days*100//total_days}%) |",
        f"| 🟡 Días parciales | {yellow_days} ({yellow_days*100//total_days}%) |",
        f"| 🔴 Días sin datos | {red_days} ({red_days*100//total_days}%) |",
        f"| Total ejecuciones | {sum(e['total'] for e in exec_data.values()):,} |",
        "",
        "---",
        "",
        "## Calendario por mes",
        "",
    ]

    # Build months in reverse (most recent first)
    for year, month in reversed(months):
        table = build_month_table(year, month, all_days, exec_data, et0_data, ubi_data, irr_data, temp_data)
        lines.append(table)
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    content = generate_status_md()
    output_path = os.path.join(os.path.dirname(__file__), "..", "STATUS.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"STATUS.md generated successfully.")
