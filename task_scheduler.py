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

def scheduled_sendgrid_job():
    logging.info("Ejecutando test_sendgrid.py...")
    result = subprocess.run(["python3", "test_sendgrid.py"], capture_output=True, text=True)
    logging.info(f"Salida de test_sendgrid.py: {result.stdout}")
    if result.stderr:
        logging.error(f"Errores de test_sendgrid.py: {result.stderr}")

scheduler = BackgroundScheduler()

def schedule_tasks():
    # run.py
    scheduler.add_job(scheduled_job, 'cron', hour='01', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='02', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='03', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='04', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='05', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='06', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='07', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='08', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='09', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='10', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='11', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='12', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='13', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='14', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='15', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='16', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='17', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='18', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='19', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='20', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='21', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='22', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='23', minute='00')
    scheduler.add_job(scheduled_job, 'cron', hour='00', minute='00')

    # sendgrid
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='00', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='01', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='02', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='03', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='04', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='05', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='06', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='07', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='08', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='09', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='10', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='11', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='12', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='13', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='14', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='15', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='16', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='17', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='18', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='19', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='20', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='21', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='22', minute='08')
    scheduler.add_job(scheduled_sendgrid_job, 'cron', hour='23', minute='08')

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

