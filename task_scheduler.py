# Schedule application executions and save the data of these executions

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import time
from app import create_app, db
from app.models import ExecutionLog
from app.services.wiseconn import run_fetch_process

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

app = create_app()
def scheduled_job():
    with app.app_context():
        results, status_wiseconn, status_ubibot = run_fetch_process()
        log = ExecutionLog(
            status_wiseconn=status_wiseconn,
            status_ubibot=status_ubibot,
            date=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        logging.info(f"Registro añadido con estados - Wiseconn: {status_wiseconn}, Ubibot: {status_ubibot}")

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