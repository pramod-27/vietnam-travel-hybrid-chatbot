# utils/logger.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import Config

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("hybrid_travel")
logger.setLevel(logging.INFO)

log_file = Path(Config.LOG_FILE)
handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=3)
fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
handler.setFormatter(fmt)
logger.addHandler(handler)

# console
ch = logging.StreamHandler()
ch.setFormatter(fmt)
logger.addHandler(ch)

# small helpers
def log_info(msg):
    logger.info(msg)

def log_error(msg):
    logger.error(msg)

def log_warning(msg):
    logger.warning(msg)

def log_success(msg):
    logger.info(f"SUCCESS: {msg}")