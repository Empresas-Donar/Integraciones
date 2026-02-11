import logging
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

def scheduled_job():
    logging.info("Ejecutando run.py...")
    result = subprocess.run(["python3", "run.py"], capture_output=True, text=True)
    logging.info(f"Salida de run.py: {result.stdout}")
    if result.stderr:
        logging.error(f"Errores de run.py: {result.stderr}")

def scheduled_sendgrid_job():
    logging.info("Ejecutando daily_channel_report.py...")
    result = subprocess.run(["python3", "daily_channel_report.py"], capture_output=True, text=True)
    logging.info(f"Salida de daily_channel_report.py: {result.stdout}")
    if result.stderr:
        logging.error(f"Errores de daily_channel_report.py: {result.stderr}")

scheduler = BackgroundScheduler()

def add_jobs(scheduler, job_function, times):
    for hour, minute in times:
        scheduler.add_job(job_function, 'cron', hour=hour, minute=minute)

scheduled_times = [(hour, '00') for hour in range(24)]
sendgrid_times = [(7, '20')]

def schedule_tasks():
    add_jobs(scheduler, scheduled_job, scheduled_times)
    add_jobs(scheduler, scheduled_sendgrid_job, sendgrid_times)

if __name__ == "__main__":
    print("Programando tareas...", flush=True)
    schedule_tasks()
    print("Tareas programadas. Scheduler iniciará.", flush=True)
    scheduler.start()
    print("Scheduler iniciado.", flush=True)
    try:
        while True:
            time.sleep(20)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Scheduler detenido.", flush=True)
