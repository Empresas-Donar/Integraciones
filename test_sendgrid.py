import os
from sqlalchemy import create_engine
from app import db 
from app.mail_class import MailManager
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

mail_manager = MailManager(session)
canales_info = mail_manager.channels_down()
sensores_info = mail_manager.sensors_down()

canales_message = "Canales apagados con net=0:\n" + ", ".join(f"Canal: {channel_id}, Nombre: {name}" for channel_id, name in canales_info)
email_content = f"Reporte de Canales y Sensores Fallidos\n{canales_message}\n{sensores_info}"

if canales_info or sensores_info.strip():
    mail_manager.enviar_email("Reporte de Canales y Sensores Fallidos", email_content)
else:
    print("No hay canales ni sensores fallidos en las últimas horas. No se enviará ningún correo.")

session.close()
