import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from datetime import datetime, timedelta
import pytz
from sqlalchemy.orm import sessionmaker
from .models import UbibotChannels, UbibotFields
from sqlalchemy import create_engine, and_

class MailManager:
    def __init__(self, session):
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
        self.from_email = Email("bot@empresasdonar.cl")
        self.to_email = To("gestion@empresasdonar.cl")
        self.session = session 

    def channels_down(self):
        filtered_data = self.session.query(UbibotChannels.channel_id, UbibotChannels.name).filter(
            UbibotChannels.net == 0
        ).distinct().all()
        return [(data.channel_id, data.name) for data in filtered_data]

    def sensors_down(self):
        chile_tz = pytz.timezone('America/Santiago')
        fecha_actual_chile = datetime.now(chile_tz).date()
        hora_actual_chile = datetime.now(chile_tz).time()
        hora_inicio_chile = (datetime.now(chile_tz) - timedelta(minutes=90)).time()
        resultados = self.session.query(UbibotFields).filter(
            UbibotFields.date == fecha_actual_chile,
            UbibotFields.hour.between(hora_inicio_chile, hora_actual_chile),
            and_(
                UbibotFields.avg == 0,
                UbibotFields.count == 0,
                UbibotFields.min == 0,
                UbibotFields.max == 0
            )
        ).all()

        message = "Sensores apagados en las últimas horas:\n"
        for resultado in resultados:
            message += f"Canal: {resultado.channel_id}, Nombre: {resultado.name}, Hora: {resultado.hour}, Fecha: {resultado.date}\n"
        return message 

    def enviar_email(self, subject, content):
        mail = Mail(self.from_email, self.to_email, subject, Content("text/plain", content))
        try:
            response = self.sg.send(mail)
            print(f"Email enviado! Código de estado: {response.status_code}")
        except Exception as e:
            print(f"Error al enviar el email: {str(e)}")