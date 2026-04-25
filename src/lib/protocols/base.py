from abc import ABC, abstractmethod
import socket
import logging

from lib.constants import MAX_RETRANSMIT_ATTEMPTS, SR_RETRANSMIT_TIMEOUT


class TransferStrategy(ABC):
    def __init__(self, sock: socket.socket, server_addr: tuple, logger: logging.Logger):
        self.sock = sock
        self.server_addr = server_addr
        self.logger = logger
        self.max_attempts = MAX_RETRANSMIT_ATTEMPTS
        self.timeout_limit = SR_RETRANSMIT_TIMEOUT

    @abstractmethod
    def transfer(self, local_path: str, start_seq_num: int) -> int:
        pass