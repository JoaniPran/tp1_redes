import os
import logging


def setup_logger(verbose: bool, quiet: bool, name: str) -> logging.Logger:
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.ERROR
    else:
        level = logging.INFO

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=level,
    )
    return logging.getLogger(name)

def check_file(file_path: str, logger: logging.Logger) -> bool:
    if not os.path.exists(file_path):
        logger.error(f"{file_path} does not exist.")
        return False
    if not os.path.isfile(file_path):
        logger.error(f"{file_path} is a directory.")
        return False
    return True