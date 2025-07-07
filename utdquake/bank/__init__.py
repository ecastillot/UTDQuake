import logging

def setup_logger(logging_level=logging.INFO):
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