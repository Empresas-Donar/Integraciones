import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.mail_class import MailManager
from app.ubi_alert_class import UbibotAlertManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def send_email_if_not_empty(mail_manager, subject, content):
    if content:
        email_content = f"Reporte de Canales Fallidos\n\n{content}"
        mail_manager.send_mail(subject, email_content)
        logging.info(f"Correo enviado: {subject}")


def main():
    DATABASE_URL = os.getenv('DATABASE_URL')
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        alert_manager = UbibotAlertManager(session)
        mail_manager = MailManager()
        channels_info = alert_manager.channels_down()

        logging.info(f"Canales caídos encontrados: {len(channels_info)}")

        z_k_channels = [f"- Canal: {channel_id}, Nombre: {name}" for channel_id, name in channels_info if name.startswith("Z") or name.startswith("K")]
        t_i_channels = [f"- Canal: {channel_id}, Nombre: {name}" for channel_id, name in channels_info if name.startswith("T") or name.startswith("I")]
        other_channels = [f"- Canal: {channel_id}, Nombre: {name}" for channel_id, name in channels_info if not (name.startswith("Z") or name.startswith("K") or name.startswith("T") or name.startswith("I"))]

        send_email_if_not_empty(
            mail_manager,
            "Reporte de Canales Zuñiga y Kontrolag",
            "Canales con prefijos Z y K:\n" + "\n".join(z_k_channels + other_channels)
        )

        send_email_if_not_empty(
            mail_manager,
            "Reporte de Canales Talagante e Isla de Maipo",
            "Canales con prefijos T e I:\n" + "\n".join(t_i_channels)
        )

        # Reporte de sensores caídos
        sensors_report = alert_manager.sensors_down()
        sensors_lines = sensors_report.split("\n")
        if len(sensors_lines) > 1:  # Más que solo el header
            logging.info(f"Sensores caídos encontrados: {len(sensors_lines) - 1}")
            mail_manager.send_mail(
                "Reporte de Sensores Caídos",
                sensors_report
            )
            logging.info("Correo enviado: Reporte de Sensores Caídos")
        else:
            logging.info("No hay sensores caídos")

        logging.info("Reporte diario completado")
    except Exception as e:
        logging.error(f"Error en reporte diario: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
