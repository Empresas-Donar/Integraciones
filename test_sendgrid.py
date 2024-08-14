import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db 
from app.mail_class import MailManager, UbibotAlertManager 

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

alert_manager = UbibotAlertManager(session)
mail_manager = MailManager()
channels_info = alert_manager.channels_down()
sensors_info = alert_manager.sensors_down()
channels_message = "Canales apagados:\n" + ", ".join(f"Canal: {channel_id}, Nombre: {name}" for channel_id, name in channels_info)
email_content = f"Reporte de Canales y Sensores Fallidos\n{channels_message}\n{sensors_info}"

if channels_info or sensors_info.strip():
    mail_manager.send_mail("Reporte de Canales y Sensores Fallidos", email_content)
else:
    print("No hay canales ni sensores fallidos en las últimas horas. No se enviará ningún correo.")
session.close()
