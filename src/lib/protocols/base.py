from abc import ABC, abstractmethod
import socket
import logging


from lib.constants import MAX_NETWORK_ATTEMPTS, LIMIT_TIMEOUTS

class TransferStrategy(ABC):
    def __init__(self, sock: socket.socket, server_addr: tuple, logger: logging.Logger):
        self.sock = sock
        self.server_addr = server_addr
        self.logger = logger
        self.max_attempts = MAX_NETWORK_ATTEMPTS
        self.timeout_limit = LIMIT_TIMEOUTS

    @abstractmethod
    def transfer(self, local_path: str, start_seq_num: int) -> int:
        pass

    @abstractmethod
    def receive(self, local_path: str):
        pass