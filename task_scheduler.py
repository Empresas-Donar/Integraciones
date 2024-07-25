import logging
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

def scheduled_job():
    logging.info("Ejecutando run.py...")
    result = subprocess.run(["python3", "run.py"], capture_output=True, text=True)
    logging.info(f"Salida de run.py: {result.stdout}")
    if result.stderr:
        logging.error(f"Errores de run.py: {result.stderr}")

scheduler = BackgroundScheduler()

def schedule_tasks():
    scheduler.add_job(scheduled_job, 'cron', hour='07', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='12', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='18', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='22', minute='00')

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

