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
    logging.info("Ejecutando test_sendgrid.py...")
    result = subprocess.run(["python3", "test_sendgrid.py"], capture_output=True, text=True)
    logging.info(f"Salida de test_sendgrid.py: {result.stdout}")
    if result.stderr:
        logging.error(f"Errores de test_sendgrid.py: {result.stderr}")

scheduler = BackgroundScheduler()

def add_jobs(scheduler, job_function, times):
    for hour, minute in times:
        scheduler.add_job(job_function, 'cron', hour=hour, minute=minute)

scheduled_times = [(hour, '00') for hour in range(24)]
sendgrid_times = [(hour, '20') for hour in range(24)]

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
