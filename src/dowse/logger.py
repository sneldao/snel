import logging
import sys

logger = logging.getLogger("dowse")

logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)

file_handler = logging.FileHandler("info.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)
