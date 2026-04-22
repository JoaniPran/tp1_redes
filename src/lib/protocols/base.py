from abc import ABC, abstractmethod
import socket
import logging


class TransferStrategy(ABC):
    def __init__(self, sock: socket.socket, server_addr: tuple, logger: logging.Logger):
        self.sock = sock
        self.server_addr = server_addr
        self.logger = logger
        self.max_attempts = 25
        self.timeout_limit = 0.5

    @abstractmethod
    def transfer(self, local_path: str, start_seq_num: int) -> int:
        pass