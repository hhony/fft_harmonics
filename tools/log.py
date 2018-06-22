from logging import getLogger, Logger, Formatter, DEBUG, StreamHandler, _nameToLevel


channel = StreamHandler()


def set_level(level: str):
    global logger
    logger = get_logger(level=level)


def get_logger(name=__name__, level='INFO') -> Logger:
    global logger, channel
    logger = getLogger(name)
    _level = _nameToLevel[level]

    channel.setLevel(_level)
    if _level == DEBUG:
        formatter = Formatter(
            "[%(levelname)s] %(funcName)s: - %(message)s")
        channel.setFormatter(formatter)
    else:
        formatter = Formatter(
            "[%(levelname)s] %(message)s")
        channel.setFormatter(formatter)
    logger.setLevel(_level)

    logger.addHandler(channel)
    return logger


logger = get_logger()