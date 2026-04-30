import socket
import logging

from abc import ABC, abstractmethod
from lib.constants import MAX_NETWORK_ATTEMPTS, DATA_TRANSFER_TIMEOUT


class RDTProtocol(ABC):
    def __init__(self, sock: socket.socket, target_addr: tuple, logger: logging.Logger):
        self.sock = sock
        self.target_addr = target_addr
        self.logger = logger

        self.max_attempts = MAX_NETWORK_ATTEMPTS
        self.timeout_limit = DATA_TRANSFER_TIMEOUT

    @abstractmethod
    def send_file(self, file_path: str, start_seq_num: int) -> int:
        pass

    @abstractmethod
    def receive_file(self, dest_path: str, expected_seq: int) -> bool:
        pass


