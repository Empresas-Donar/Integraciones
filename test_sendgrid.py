import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db 
from app.mail_class import MailManager
from app.ubi_alert_class import UbibotAlertManager

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

alert_manager = UbibotAlertManager(session)
mail_manager = MailManager()
channels_info = alert_manager.channels_down()

z_k_channels = [f"- Canal: {channel_id}, Nombre: {name}" for channel_id, name in channels_info if name.startswith("Z") or name.startswith("K")]
t_i_channels = [f"- Canal: {channel_id}, Nombre: {name}" for channel_id, name in channels_info if name.startswith("T") or name.startswith("I")]
other_channels = [f"- Canal: {channel_id}, Nombre: {name}" for channel_id, name in channels_info if not (name.startswith("Z") or name.startswith("K") or name.startswith("T") or name.startswith("I"))]


def send_email_if_not_empty(subject, content):
    if content:
        email_content = f"Reporte de Canales Fallidos\n\n{content}"
        mail_manager.send_mail(subject, email_content)


send_email_if_not_empty(
    "Reporte de Canales Z y K",
    "Canales con prefijos Z y K:\n" + "\n".join(z_k_channels)
)

send_email_if_not_empty(
    "Reporte de Canales T e I",
    "Canales con prefijos T e I:\n" + "\n".join(t_i_channels)
)

send_email_if_not_empty(
    "Reporte de Otros Canales",
    "Otros canales:\n" + "\n".join(other_channels)
)

session.close()