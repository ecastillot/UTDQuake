import os
import logging

def setup_logger(logging_level=logging.INFO,log_file=None):
    """
    Set up a logger that includes module name, function name, and line number
    for DEBUG level. INFO and higher levels use a cleaner format.

    Parameters:
    logging_level (int): Logging level from the logging module (e.g., logging.DEBUG, logging.INFO).
    """

    # Choose format depending on logging level
    if logging_level == logging.DEBUG:
        fmt = "%(asctime)s [%(levelname)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s"
    else:
        fmt = "%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s"

    # Clear any existing handlers (to avoid duplicate logs if re-run)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging_level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if log_file is not None:
        # Ensure the log file directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        add_file_handler(log_file)

def add_file_handler(log_file, logger=None, level=None):
    """
    Add a FileHandler to the given logger if not already present.

    Parameters
    ----------
    log_file : str
        Path to the log file.
    logger : logging.Logger or None
        The logger to add the handler to. If None, uses the root logger.
    level : int or None
        Logging level for the file handler. If None, uses logger's level.
    """
    logger = logger or logging.getLogger()


    # Remove all file handlers first
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)


    if level is None:
        level = logger.level
    # Ensure parent dir exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Add handler only if not present
    if not any(
        isinstance(h, logging.FileHandler) and h.baseFilename == os.path.abspath(log_file)
        for h in logger.handlers
    ):
        file_handler = logging.FileHandler(log_file, mode="a")
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
        logger.info(f"Added file handler: {log_file}")

    return log_file