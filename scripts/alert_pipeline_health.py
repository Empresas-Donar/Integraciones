"""
Pipeline health alert — sends email if no successful execution in the last 2 hours.

Run via Cloud Scheduler every 2 hours:
  schedule: "0 */2 * * *"
  target: this script (or as a Cloud Run Job)

Environment variables required:
  DATABASE_URL   — PostgreSQL connection string
  RESEND_API_KEY — Resend API key
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import psycopg2
import resend

DB_URL = os.environ["DATABASE_URL"]
THRESHOLD_HOURS = 2


def check_last_execution(cur):
    cur.execute("""
        SELECT
            date AT TIME ZONE 'America/Santiago' AS fecha_santiago,
            status_wiseconn,
            status_ubibot
        FROM execution_log
        ORDER BY date DESC
        LIMIT 1;
    """)
    return cur.fetchone()


def send_alert(last_exec, hours_since):
    resend.api_key = os.environ["RESEND_API_KEY"]

    if last_exec:
        last_time = last_exec[0].strftime("%Y-%m-%d %H:%M:%S")
        detail = (
            f"Última ejecución: {last_time} (hora Santiago)\n"
            f"  Wiseconn: {last_exec[1]}\n"
            f"  Ubibot:   {last_exec[2]}\n"
            f"  Hace:     {hours_since:.1f} horas"
        )
    else:
        detail = "No se encontraron ejecuciones en execution_log."

    body = (
        f"ALERTA: El pipeline de integración lleva más de {THRESHOLD_HOURS} horas sin ejecutarse.\n\n"
        f"{detail}\n\n"
        f"Acciones sugeridas:\n"
        f"  1. Revisar Cloud Run Jobs: https://console.cloud.google.com/run/jobs?project=integraciones-484915\n"
        f"  2. Resetear el scheduler si está stuck:\n"
        f"     gcloud scheduler jobs pause integraciones-hourly --location=southamerica-east1 --project=integraciones-484915\n"
        f"     gcloud scheduler jobs resume integraciones-hourly --location=southamerica-east1 --project=integraciones-484915\n"
        f"  3. Forzar ejecución manual:\n"
        f"     gcloud run jobs execute integraciones-job --region=southamerica-west1 --project=integraciones-484915\n"
    )

    resend.Emails.send({
        "from": "Integraciones Bot <onboarding@resend.dev>",
        "to": "gestion@empresasdonar.cl",
        "subject": f"[ALERTA] Pipeline caído — {hours_since:.1f}h sin ejecuciones",
        "text": body,
    })
    print(f"Alerta enviada. Última ejecución hace {hours_since:.1f}h.")


def run():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    last_exec = check_last_execution(cur)
    conn.close()

    now_utc = datetime.now(timezone.utc)

    if last_exec is None:
        send_alert(None, 999)
        sys.exit(0)

    # execution_log.date is timestamptz — compare in UTC
    cur2_conn = psycopg2.connect(DB_URL)
    cur2 = cur2_conn.cursor()
    cur2.execute("SELECT date FROM execution_log ORDER BY date DESC LIMIT 1;")
    last_date_utc = cur2.fetchone()[0]
    cur2_conn.close()

    # Ensure timezone-aware comparison
    if last_date_utc.tzinfo is None:
        last_date_utc = last_date_utc.replace(tzinfo=timezone.utc)

    hours_since = (now_utc - last_date_utc).total_seconds() / 3600

    if hours_since >= THRESHOLD_HOURS:
        send_alert(last_exec, hours_since)
    else:
        print(f"Pipeline OK — última ejecución hace {hours_since:.1f}h.")


if __name__ == "__main__":
    run()
