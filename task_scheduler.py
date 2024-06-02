# task schedule config

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from run import main as run_main
from datetime import datetime
import time
from app import create_app, db
from app.models import ExecutionLog

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logging.getLogger('apscheduler').setLevel(logging.DEBUG)
app = create_app()

def scheduled_job():
    with app.app_context():
        status = 'Success'
        try:
            print(f"Ejecutando tarea programada a las {datetime.now()}...", flush=True)
            run_main()
        except Exception as e:
            status = f'Failed: {e}'
            print(f"Error durante la ejecución: {e}", flush=True)
        finally:
            # Registrar la ejecución
            log = ExecutionLog(status=status, date=datetime.utcnow())
            db.session.add(log)
            db.session.commit()
scheduler = BackgroundScheduler()

print("Programando tareas...", flush=True)
scheduler.add_job(scheduled_job, 'cron', hour='07', minute='0')
scheduler.add_job(scheduled_job, 'cron', hour='12', minute='0')
scheduler.add_job(scheduled_job, 'cron', hour='18', minute='0')
scheduler.add_job(scheduled_job, 'cron', hour='22', minute='0')
print("Tareas programadas. Scheduler iniciará.", flush=True)

scheduler.start()
print("Scheduler iniciado.", flush=True)

try:
    while True:
        time.sleep(20)  
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()  
    print("Scheduler detenido.", flush=True)
