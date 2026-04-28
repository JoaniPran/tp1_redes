import socket
import threading
import os

from lib.datagrams.datagram import Datagram
from lib.datagrams.handshake import HandshakeDatagram
from lib.datagrams.error import ErrorDatagram
from lib.constants import MAX_FILE_SIZE, SOCKET_RECV_BUFFER
from lib.server.worker import Worker
from lib.server.downloadWorker import DownloadWorker
from lib.datagrams.donwload import DownloadRequestDatagram


class ServerDispatcher:
    def __init__(self, host: str, port: int, storage: str, logger):
        self.addr = (host, port)
        self.storage = storage
        self.logger = logger
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        os.makedirs(self.storage, exist_ok=True)

    def start(self):
        self.sock.bind(self.addr)
        self.logger.info(f"Dispatcher listening on {self.addr}. Storage: {self.storage}")

        while True:
            data, client_addr = self.sock.recvfrom(SOCKET_RECV_BUFFER)
            try:
                packet = Datagram.from_bytes(data)
                if isinstance(packet, HandshakeDatagram):
                    if packet.file_size > MAX_FILE_SIZE:
                        error_pkt = ErrorDatagram("File too large. Max 20MB.")
                        self.sock.sendto(error_pkt.to_bytes(), client_addr)
                        continue

                    self.logger.info(f"New Handshake from {client_addr} for file: {packet.file_name}")
                    worker = Worker(client_addr, packet, self.storage, self.logger)
                    worker_thread = threading.Thread(target=worker.run)
                    worker_thread.daemon = True
                    worker_thread.start()

                elif isinstance(packet, DownloadRequestDatagram):
                    self.logger.info(f"Descarga detectada desde {client_addr} para {packet.file_name}")
                    # Lanzamos el nuevo worker que creamos antes
                    worker = DownloadWorker(client_addr, packet.file_name, self.storage, self.logger)
                    worker_thread = threading.Thread(target=worker.run)
                    worker_thread.daemon = True # hilo muere inmediatamente si el programa principal (el servidor) se cierra.
                    worker_thread.start() #worker_thread.start(), el Worker empieza a correr su método run() en un hilo separado.
                else:
                    self.logger.warning(f"Ignored packet on port {self.addr}: Unexpected Opcode.")

            except Exception as e:
                self.logger.debug(f"Garbage received or error parsing datagram: {e}")