"""Recalculate dynamic-model chill portions once a night.

The hourly pipeline must not call this. refresh_ubi_chill_portions()
rewrites the current year for every channel and saturates Cloud SQL.
"""

import logging

from app import create_app, db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

app = create_app()


def main():
    with app.app_context():
        logging.info("Refreshing ubi_chill_portions")
        db.session.execute(db.text("SELECT refresh_ubi_chill_portions()"))
        db.session.commit()
        logging.info("ubi_chill_portions refresh finished")


if __name__ == "__main__":
    main()
