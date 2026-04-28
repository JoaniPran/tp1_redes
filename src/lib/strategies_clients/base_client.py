
from abc import ABC, abstractmethod

import socket
import logging
import os

from lib.datagrams.datagram import Datagram
from lib.datagrams.handshake import HandshakeDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.protocols.stop_and_wait import StopAndWaitStrategy
from lib.protocols.selective_repeat import SelectiveRepeatStrategy



from lib.constants import MAX_NETWORK_ATTEMPTS


class ClientStrategy(ABC):
    def __init__(self, host: str, port: int, protocol_name: str, logger: logging.Logger):
        self.server_addr = (host, port)
        self.protocol_name = protocol_name
        self.logger = logger
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.max_attempts = MAX_NETWORK_ATTEMPTS
        self.next_seq_num = 1

  