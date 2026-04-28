import socket
import logging
import os

from lib.datagrams.datagram import Datagram
from lib.datagrams.donwload import DownloadRequestDatagram
from lib.datagrams.ack import AckDatagram
# Aquí importarás las estrategias de recepción, que son distintas a las de envío
from lib.protocols.stop_and_wait import StopAndWaitStrategy
from lib.strategies_clients.base_client import ClientStrategy

from lib.constants import SOCKET_RECV_BUFFER

class ClientDownloader(ClientStrategy):
    def download_file(self, remote_name: str, local_path: str):
        # 1. Fase de pedido (Handshake de descarga)
        self._request_phase(remote_name)

        # 2. Elegir estrategia de recepción
        if self.protocol_name == 'sw':
            strategy = StopAndWaitStrategy(self.sock, self.server_addr, self.logger)
        else:
            raise ValueError("Protocolo no soportado")

        # 3. Transferencia (Recibir datos y escribir en disco)
        strategy.receive(local_path)
        
        self.logger.info(f"Archivo guardado en {local_path}")
        self.sock.close()

    def _request_phase(self, remote_name: str):
        self.logger.debug(f"Enviando pedido de descarga para: {remote_name}")
        self.sock.settimeout(1.0)

        # Opcode 1: Download Request
        request_packet = DownloadRequestDatagram(remote_name)
        bytes_to_send = request_packet.to_bytes()

        attempts = 0
        while attempts < self.max_attempts:
            self.sock.sendto(bytes_to_send, self.server_addr)
            try:
                # Esperamos la respuesta del servidor. 
                # El servidor debería responder con el puerto del Worker.
                data, new_addr = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                response = Datagram.from_bytes(data)

                # El Worker de descarga enviará un ACK(0) para confirmar que el archivo existe
                if isinstance(response, AckDatagram) and response.seq_num == 0:
                    self.server_addr = new_addr
                    self.logger.debug(f"Pedido aceptado por el Worker en {new_addr}")
                    return
            except socket.timeout:
                attempts += 1
                self.logger.warning(f"Reintentando pedido ({attempts}/{self.max_attempts})")

        raise ConnectionError("El servidor no respondió al pedido de descarga o el archivo no existe.")