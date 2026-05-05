import socket
import os
import logging

from lib.datagrams.ack import AckDatagram
from lib.datagrams.handshake import HandshakeDatagram
from lib.protocols.stop_and_wait import StopAndWaitProtocol
from lib.protocols.selective_repeat import SelectiveRepeatProtocol
from lib.helpers import send_error_reliably
from lib.constants import WORKER_SOCKET_TIMEOUT, SR_STRATEGY, SW_STRATEGY


class UploadWorker:
    def __init__(self, client_addr: tuple, hs_packet: HandshakeDatagram, storage: str, logger: logging.Logger):
        self.client_addr = client_addr
        self.hs = hs_packet
        self.logger = logger

        safe_name = os.path.basename(self.hs.file_name)
        self.final_path = os.path.join(storage, safe_name)
        unique_id = os.getpid()
        self.temp_path = os.path.join(storage, f".tmp_{client_addr[1]}_{unique_id}_{safe_name}")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.sock.settimeout(WORKER_SOCKET_TIMEOUT)

    def run(self):
        local_port = self.sock.getsockname()[1]
        self.logger.debug(f"UploadWorker started on port {local_port} for {self.client_addr}")

        ack_hs = AckDatagram(0)
        self.sock.sendto(ack_hs.to_bytes(), self.client_addr)

        if self.hs.protocol == SR_STRATEGY:
            protocol = SelectiveRepeatProtocol(self.sock, self.client_addr, self.logger)
        elif self.hs.protocol == SW_STRATEGY:
            protocol = StopAndWaitProtocol(self.sock, self.client_addr, self.logger)
        else:
            error_msg = f"Unsupported protocol: {self.hs.protocol}"
            self.logger.error(error_msg)
            send_error_reliably(self.sock, self.client_addr, error_msg)
            self.sock.close()
            return

        try:
            success = protocol.receive_file(self.temp_path, expected_seq=1)

            if success:
                os.replace(self.temp_path, self.final_path)
                self.logger.info(f"Upload completed: {self.final_path}")
            else:
                error_msg = "Upload failed unexpectedly"
                send_error_reliably(self.sock, self.client_addr, error_msg)

        except ConnectionError as e:
            self.logger.error(f"Connection error on port {local_port}: {e}")
            send_error_reliably(self.sock, self.client_addr, f"Connection error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error on port {local_port}: {e}")
            send_error_reliably(self.sock, self.client_addr, f"Unexpected server error: {e}")
        finally:
            if not os.path.exists(self.final_path) and os.path.exists(self.temp_path):
                os.remove(self.temp_path)
            self.sock.close()
