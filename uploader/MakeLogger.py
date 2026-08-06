import logging

def MakeLogger(name = __name__,
               log_format = '%(asctime)s %(levelname)s:%(name)s %(message)s',
               printlevel = logging.DEBUG,
               loglevel = logging.INFO,
               logfile = None):
    """
    make logger with stream and file handler
    """
    formatter = logging.Formatter(log_format)
    logger = logging.getLogger(name)
    logger.setLevel(min(printlevel, loglevel))
    
    # printing to console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(printlevel)
    logger.addHandler(stream_handler)

    # writing to file if requested
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(loglevel)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {logfile}")

    return logger