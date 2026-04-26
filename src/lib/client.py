import socket
import logging
import os

from lib.datagrams.datagram import Datagram
from lib.datagrams.handshake import HandshakeDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.protocols.stop_and_wait import StopAndWaitStrategy
from lib.protocols.selective_repeat import SelectiveRepeatStrategy
from lib.constants import MAX_FILE_SIZE, MAX_NETWORK_ATTEMPTS


class Uploader:
    def __init__(self, host: str, port: int, protocol_name: str, logger: logging.Logger):
        self.server_addr = (host, port)
        self.protocol_name = protocol_name
        self.logger = logger
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.max_attempts = 25
        self.next_seq_num = 1

    def upload_file(self, local_path: str, remote_name: str):
        file_size = os.path.getsize(local_path)
        if file_size > MAX_FILE_SIZE:
            self.logger.error(f"File size ({file_size} bytes) exceeds the 20MB limit.")
            raise ValueError("File size exceeds the 20MB limit.")

        self._handshake_phase(remote_name, file_size)

        if self.protocol_name == "sr":
            strategy = SelectiveRepeatStrategy(self.sock, self.server_addr, self.logger)
        elif self.protocol_name == 'sw':
            strategy = StopAndWaitStrategy(self.sock, self.server_addr, self.logger)
        else:
            raise ValueError(f"Protocol '{self.protocol_name}' not supported.")

        self.next_seq_num = strategy.transfer(local_path, self.next_seq_num)
        self._teardown_phase()
        self.sock.close()

    def _handshake_phase(self, remote_name: str, file_size: int):
        self.logger.debug("Starting handshake...")
        self.sock.settimeout(0.2)

        hs_packet = HandshakeDatagram(remote_name, self.protocol_name, file_size)
        bytes_to_send = hs_packet.to_bytes()

        attempts = 0
        while attempts < self.max_attempts:
            self.sock.sendto(bytes_to_send, self.server_addr)
            try:
                data, new_addr = self.sock.recvfrom(1024)
                response = Datagram.from_bytes(data)

                if isinstance(response, AckDatagram) and response.seq_num == 0:
                    self.server_addr = new_addr
                    self.logger.debug(f"Handshake successful. Assigned Worker: {new_addr}")
                    return
            except socket.timeout:
                attempts += 1
                self.logger.warning(f"Handshake Timeout ({attempts}/{self.max_attempts})")

        raise ConnectionError("Could not contact the server.")

    def _teardown_phase(self):
        self.logger.debug("Starting Secure Teardown...")
        self.sock.setblocking(True)
        self.sock.settimeout(0.2)

        close_packet = CloseDatagram(self.next_seq_num)
        close_bytes = close_packet.to_bytes()

        attempts = 0
        while attempts < self.max_attempts:
            self.sock.sendto(close_bytes, self.server_addr)
            try:
                data, _ = self.sock.recvfrom(2048)
                response = Datagram.from_bytes(data)

                if isinstance(response, AckDatagram) and response.seq_num == self.next_seq_num:
                    self.logger.debug("Teardown confirmed by the server.")
                    return
            except socket.timeout:
                attempts += 1

        self.logger.warning("No teardown ACK received, assuming successful delivery.")
