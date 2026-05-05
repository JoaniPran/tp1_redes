import socket
import threading
import os
import time

from lib.datagrams.datagram import Datagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.handshake import HandshakeDatagram
from lib.server.upload_worker import UploadWorker
from lib.server.download_worker import DownloadWorker
from lib.datagrams.download import DownloadRequestDatagram
from lib.helpers import send_error_reliably
from lib.constants import MAX_FILE_SIZE, SOCKET_RECV_BUFFER


class ServerDispatcher:
    def __init__(self, host: str, port: int, storage: str, logger):
        self.addr = (host, port)
        self.storage = storage
        self.logger = logger
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        os.makedirs(self.storage, exist_ok=True)

        self._active_transfers = {}
        self._lock = threading.Lock()

    def _cleanup_old_transfers(self, max_age: float = 60.0):
        now = time.time()
        with self._lock:
            expired = [k for k, t in self._active_transfers.items() if now - t > max_age]
            for k in expired:
                del self._active_transfers[k]

    def start(self):
        self.sock.bind(self.addr)
        self.logger.info(f"Dispatcher listening on {self.addr}. Storage: {self.storage}")

        while True:
            data, client_addr = self.sock.recvfrom(SOCKET_RECV_BUFFER)
            try:
                packet = Datagram.from_bytes(data)

                if isinstance(packet, HandshakeDatagram):
                    if not packet.file_name or packet.file_name.isspace():
                        send_error_reliably(self.sock, client_addr, "Invalid file name")
                        continue

                    if packet.file_size > MAX_FILE_SIZE:
                        send_error_reliably(
                            self.sock,
                            client_addr,
                            f"File too large. Maximum allowed size is {MAX_FILE_SIZE} bytes.")
                        continue

                    key = (client_addr, packet.file_name)
                    with self._lock:
                        if key in self._active_transfers:
                            self.logger.debug(f"Duplicate upload request from {client_addr}, resending ACK...")
                            worker_ref = self._active_transfers[key].get('worker')
                            if worker_ref:
                                ack_hs = AckDatagram(0)
                                worker_ref.sock.sendto(ack_hs.to_bytes(), client_addr)
                            continue

                        worker = UploadWorker(client_addr, packet, self.storage, self.logger)
                        self._active_transfers[key] = {'time': time.time(), 'worker': worker}

                    self.logger.info(f"New Handshake from {client_addr} for file: {packet.file_name}")

                    def run_upload_worker(w, key):
                        try:
                            w.run()
                        finally:
                            with self._lock:
                                self._active_transfers.pop(key, None)
                    worker_thread = threading.Thread(target=run_upload_worker, args=(worker, key))
                    worker_thread.daemon = True
                    worker_thread.start()

                elif isinstance(packet, DownloadRequestDatagram):
                    self.logger.info(f"Download request detected from {client_addr} for {packet.file_name}")

                    full_path = os.path.join(self.storage, os.path.basename(packet.file_name))
                    if not os.path.isfile(full_path):
                        send_error_reliably(self.sock, client_addr, f"File not found: {packet.file_name}")
                        continue

                    key = (client_addr, packet.file_name)
                    with self._lock:
                        if key in self._active_transfers:
                            self.logger.debug(f"Ignoring duplicate download request from {client_addr} for {packet.file_name}")
                            continue
                        self._active_transfers[key] = time.time()

                    worker = DownloadWorker(client_addr, packet.file_name, packet.protocol, self.storage, self.logger)

                    def run_download_worker(w, key):
                        try:
                            w.run()
                        finally:
                            with self._lock:
                                self._active_transfers.pop(key, None)
                    worker_thread = threading.Thread(target=run_download_worker, args=(worker, key))
                    worker_thread.daemon = True
                    worker_thread.start()
                else:
                    self.logger.warning(f"Ignored packet on port {self.addr}: Unexpected Opcode.")

                self._cleanup_old_transfers(max_age=60.0)

            except Exception as e:
                self.logger.debug(f"Garbage received or error parsing datagram: {e}")
