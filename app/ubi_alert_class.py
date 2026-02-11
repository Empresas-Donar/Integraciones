from datetime import datetime, timedelta
import pytz
from sqlalchemy import and_
from .models import UbibotChannels, UbibotFields

class UbibotAlertManager:
    def __init__(self, session):
        self.session = session
        self.chile_tz = pytz.timezone('America/Santiago')

    def get_chile_time(self):
        current_chile_time = datetime.now(self.chile_tz)
        return current_chile_time.date(), current_chile_time.time(), (current_chile_time - timedelta(minutes=90)).time()

    def channels_down(self):
        filtered_data = self.session.query(UbibotChannels.channel_id, UbibotChannels.name).filter(
            UbibotChannels.net == 0
        ).distinct().all()
        return [(data.channel_id, data.name) for data in filtered_data]

    def sensors_down(self):
        yesterday = datetime.now(self.chile_tz).date() - timedelta(days=1)
        resultados = self.session.query(UbibotFields).filter(
            UbibotFields.date == yesterday,
            UbibotFields.count == 0
        ).all()
        lines = ["Sensores sin lecturas el día anterior:"]
        for resultado in resultados:
            lines.append(f"Canal: {resultado.channel_id}, Nombre: {resultado.name}, Hora: {resultado.hour}, Fecha: {resultado.date}")
        return "\n".join(lines)