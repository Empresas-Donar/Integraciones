import os
from datetime import datetime, timedelta
import pytz
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from app.models import UbibotChannels, UbibotFields
from app import db
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
from_email = Email("bot@empresasdonar.cl")
to_email = To("gestion@empresasdonar.cl")

def canales_apagados():
    filtered_data = session.query(UbibotChannels.channel_id, UbibotChannels.name).filter(
        UbibotChannels.net == 0  
    ).distinct().all()
    return [(data.channel_id, data.name) for data in filtered_data]

def sensores_apagados():
    chile_tz = pytz.timezone('America/Santiago')
    fecha_actual_chile = datetime.now(chile_tz).date()
    hora_actual_chile = datetime.now(chile_tz).time()
    hora_inicio_chile = (datetime.now(chile_tz) - timedelta(minutes=90)).time()
    resultados = session.query(UbibotFields).filter(
        UbibotFields.date == fecha_actual_chile,
        UbibotFields.hour.between(hora_inicio_chile, hora_actual_chile), 
        and_(
            UbibotFields.avg == 0,
            UbibotFields.count == 0,
            UbibotFields.min == 0,
            UbibotFields.max == 0
        )
    ).all()

    message = "Sensores apagados en las últimas  horas:\n"
    for resultado in resultados:
        message += f"Canal: {resultado.channel_id}, Nombre: {resultado.name}, Hora: {resultado.hour}, Fecha: {resultado.date}\n"

    return message

def enviar_email(subject, content):
    mail = Mail(from_email, to_email, subject, Content("text/plain", content))
    try:
        response = sg.send(mail)
        print(f"Email enviado! Código de estado: {response.status_code}")
    except Exception as e:
        print(f"Error al enviar el email: {str(e)}")


canales_message = f"Canales apagados con net=0:\n"
canales_info = canales_apagados()
for channel_id, name in canales_info:
    canales_message += f"Canal: {channel_id}, Nombre: {name}\n"

sensores_message = sensores_apagados()

email_content = canales_message + "\n" + sensores_message

if canales_info or sensores_message.strip():
    enviar_email("Reporte de Canales y Sensores Fallidos", email_content)
else:
    print("No hay canales ni sensores fallidos en las últimas 2 horas. No se enviará ningún correo.")

session.close()