import logging
import logging.handlers
import os


def Logger(name, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not os.path.exists("logs"):
        os.makedirs("logs")

    handler = logging.handlers.RotatingFileHandler(
        f"logs/{name}.log",
        mode="a",
        encoding="utf-8",
        maxBytes=5 * 1024 * 1024,
        delay=0,
    )

    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)

    stdout_logger = logging.StreamHandler()
    stdout_logger.setLevel(logging.DEBUG)
    stdout_logger.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(stdout_logger)

    logger.info("Logger initialized, {name}, {level}".format(name=name, level=level))

    return logger
