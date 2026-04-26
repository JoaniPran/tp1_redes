from abc import ABC, abstractmethod
import socket
import logging

class ReceiverStrategy(ABC):
    def __init__(self, sock: socket.socket, client_addr: tuple, logger: logging.Logger):
        self.sock = sock
        self.client_addr = client_addr
        self.logger = logger

    @abstractmethod
    def receive(self, temp_path: str) -> bool:
        pass