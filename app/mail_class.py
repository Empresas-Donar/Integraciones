import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from sqlalchemy import create_engine, and_

class MailManager:
    def __init__(self):
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.sg = sendgrid.SendGridAPIClient(api_key=self.sendgrid_api_key)
        self.from_email = Email("bot@empresasdonar.cl")
        self.to_email = To("gestion@empresasdonar.cl")

    def send_mail(self, subject, content):
        mail = Mail(self.from_email, self.to_email, subject, Content("text/plain", content))
        try:
            response = self.sg.send(mail)
            print(f"Email enviado! Código de estado: {response.status_code}")
        except Exception as e:
            print(f"Error al enviar el email: {str(e)}")