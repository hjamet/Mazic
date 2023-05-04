import logging
import logging.handlers
import os


def Logger(name, level=logging.DEBUG, log_initialization=True):
    """Initialize a logger.

    Args:
        name (str): The name of the logger.
        level (int, optional): The level of the logger. Defaults to logging.DEBUG.
        log_initialization (bool, optional): Whether to log the initialization or not. Defaults to True.

    Returns:
        logging.Logger: The logger.
    """
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

    if log_initialization:
        logger.info(
            "Logger initialized, {name}, {level}".format(name=name, level=level)
        )

    return logger
