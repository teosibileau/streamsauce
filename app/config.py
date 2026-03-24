import logging
import os

import colorlog
from dbos import DBOSConfig
from dotenv import load_dotenv

load_dotenv()

# DBOS Configuration
dbos_config: DBOSConfig = {
    "name": "streamsauce",
    "database_url": os.environ.get(
        "DBOS_DATABASE_URL", "postgresql://dbos:dbos@0.0.0.0:5432/dbos"
    ),
}

# Logging Setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
)
handler.setFormatter(formatter)
logger.addHandler(handler)
