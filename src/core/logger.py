import logging
from colorlog import ColoredFormatter


def setup_logger(log_level):
    handler = logging.StreamHandler()

    formatter = ColoredFormatter(
        "[%(asctime)s] [%(log_color)s%(levelname)s%(reset)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger("ploupy")
    logger.addHandler(handler)
    logger.setLevel(log_level)
