import os
import logging
import time
import socket
import sys

from lib.datagrams.error import ErrorDatagram


def setup_logger(verbose: bool, quiet: bool, name: str) -> logging.Logger:
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.INFO
    else:
        level = logging.INFO

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)  

    return logger

def check_file(file_path: str, logger: logging.Logger) -> bool:
    if not os.path.exists(file_path):
        logger.error(f"{file_path} does not exist.")
        return False
    if not os.path.isfile(file_path):
        logger.error(f"{file_path} is a directory.")
        return False
    return True

def send_error_reliably(sock: socket.socket, target_addr: tuple, message: str, retries: int = 3, delay: float = 0.2):
    error_pkt = ErrorDatagram(message)
    data = error_pkt.to_bytes()
    for attempt in range(retries):
        try:
            sock.sendto(data, target_addr)
            if attempt < retries - 1:
                time.sleep(delay)
        except:
            break