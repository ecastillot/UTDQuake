import logging

def setup_logger(debug=False):
    """
    Set up a logger that includes module name, function name, and line number
    only for DEBUG level. INFO and higher levels use a cleaner format.
    """
    level = logging.DEBUG if debug else logging.INFO

    # Choose format depending on level
    if debug:
        fmt = "%(asctime)s [%(levelname)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s"
    else:
        fmt = "%(asctime)s [%(levelname)s] %(module)s.%(funcName)s - %(message)s"

    # Clear any existing handlers (to avoid duplicate logs if re-run)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
