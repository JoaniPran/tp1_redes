import os
import logging
import socket

from lib.datagrams.datagram import Datagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.protocols.stop_and_wait import StopAndWaitProtocol
from lib.protocols.selective_repeat import SelectiveRepeatProtocol
from lib.constants import WORKER_SOCKET_TIMEOUT, SR_STRATEGY, MAX_NETWORK_ATTEMPTS, ACK_BUFFER_SIZE


class DownloadWorker:
    def __init__(self, client_addr: tuple, file_name: str, protocol_name: str, storage: str, logger: logging.Logger):
        self.client_addr = client_addr
        self.logger = logger
        self.protocol_name = protocol_name
        self.file_path = os.path.join(storage, os.path.basename(file_name))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.sock.settimeout(WORKER_SOCKET_TIMEOUT)

    def run(self):
        local_port = self.sock.getsockname()[1]

        if not os.path.exists(self.file_path):
            self.logger.error(f"Archivo no encontrado: {self.file_path}")
            self.sock.close()
            return

        ack_hs = AckDatagram(0)
        self.sock.sendto(ack_hs.to_bytes(), self.client_addr)
        self.logger.debug(f"DownloadWorker iniciado en {local_port} para {self.client_addr} ({self.protocol_name})")

        if self.protocol_name == SR_STRATEGY:
            protocol = SelectiveRepeatProtocol(self.sock, self.client_addr, self.logger)
        else:
            protocol = StopAndWaitProtocol(self.sock, self.client_addr, self.logger)

        try:
            final_seq = protocol.send_file(self.file_path, seq_num=1)
            self._teardown_phase(final_seq)
            self.logger.info(f"Descarga completada: {self.file_path}")

        except ConnectionError as e:
            self.logger.error(f"Falla en el envío: {e}")
        finally:
            self.sock.close()

    def _teardown_phase(self, final_seq_num: int):
        self.logger.debug("Iniciando cierre de conexión de descarga...")
        self.sock.settimeout(0.5)

        close_packet = CloseDatagram(final_seq_num)
        bytes_to_send = close_packet.to_bytes()

        attempts = 0
        while attempts < MAX_NETWORK_ATTEMPTS:
            self.sock.sendto(bytes_to_send, self.client_addr)
            try:
                data, _ = self.sock.recvfrom(ACK_BUFFER_SIZE)
                response = Datagram.from_bytes(data)
                if isinstance(response, AckDatagram) and response.seq_num == final_seq_num:
                    return
            except socket.timeout:
                attempts += 1

        self.logger.warning("Cierre finalizado por reintentos máximos.")