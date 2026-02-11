import os
import resend

class MailManager:
    def __init__(self):
        resend.api_key = os.getenv('RESEND_API_KEY')
        self.from_email = "Integraciones Bot <onboarding@resend.dev>"
        self.to_email = "gestion@empresasdonar.cl"

    def send_mail(self, subject, content):
        try:
            response = resend.Emails.send({
                "from": self.from_email,
                "to": self.to_email,
                "subject": subject,
                "text": content
            })
            print(f"Email enviado! ID: {response['id']}")
        except Exception as e:
            print(f"Error al enviar el email: {str(e)}")