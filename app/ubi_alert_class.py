from .models import UbibotChannels


class UbibotAlertManager:
    def __init__(self, session):
        self.session = session

    def channels_down(self):
        filtered_data = self.session.query(UbibotChannels.channel_id, UbibotChannels.name).filter(
            UbibotChannels.net == 0
        ).distinct().all()
        return [(data.channel_id, data.name) for data in filtered_data]