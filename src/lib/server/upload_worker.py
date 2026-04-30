import socket
import os
import logging

from lib.datagrams.ack import AckDatagram
from lib.datagrams.handshake import HandshakeDatagram
from lib.constants import WORKER_SOCKET_TIMEOUT, SR_STRATEGY
from lib.protocols.stop_and_wait import StopAndWaitProtocol
from lib.protocols.selective_repeat import SelectiveRepeatProtocol


class UploadWorker:
    def __init__(self, client_addr: tuple, hs_packet: HandshakeDatagram, storage: str, logger: logging.Logger):
        self.client_addr = client_addr
        self.hs = hs_packet
        self.logger = logger
        
        safe_name = os.path.basename(self.hs.file_name)
        self.final_path = os.path.join(storage, safe_name)
        self.temp_path = os.path.join(storage, f".tmp_{client_addr[1]}_{safe_name}")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.sock.settimeout(WORKER_SOCKET_TIMEOUT)

    def run(self):
        local_port = self.sock.getsockname()[1]
        self.logger.debug(f"UploadWorker iniciado en puerto {local_port} para {self.client_addr}")

        ack_hs = AckDatagram(0)
        self.sock.sendto(ack_hs.to_bytes(), self.client_addr)

        if self.hs.protocol == SR_STRATEGY:
            protocol = SelectiveRepeatProtocol(self.sock, self.client_addr, self.logger)
        else:
            protocol = StopAndWaitProtocol(self.sock, self.client_addr, self.logger)

        try:
            success = protocol.receive_file(self.temp_path, expected_seq=1)

            if success:
                os.replace(self.temp_path, self.final_path)
                self.logger.info(f"Subida completada: {self.final_path}")

        except ConnectionError as e:
            self.logger.error(f"Error de conexión en puerto {local_port}: {e}")
        except Exception as e:
            self.logger.error(f"Error inesperado en puerto {local_port}: {e}")
        finally:
            if not os.path.exists(self.final_path) and os.path.exists(self.temp_path):
                os.remove(self.temp_path)
            self.sock.close()