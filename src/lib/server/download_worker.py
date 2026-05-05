import os
import logging
import socket
import time

from lib.datagrams.datagram import Datagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.datagrams.error import ErrorDatagram
from lib.protocols.stop_and_wait import StopAndWaitProtocol
from lib.protocols.selective_repeat import SelectiveRepeatProtocol
from lib.helpers import send_error_reliably
from lib.constants import (
    WORKER_SOCKET_TIMEOUT,
    SR_STRATEGY,
    SW_STRATEGY,
    MAX_NETWORK_ATTEMPTS,
    ACK_BUFFER_SIZE,
    TEARDOWN_GRACE_SECONDS,
    TEARDOWN_ACK_RETRIES,
    TEARDOWN_ACK_SLEEP,
)


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
            error_msg = f"File not found: {self.file_path}"
            self.logger.error(error_msg)
            send_error_reliably(self.sock, self.client_addr, error_msg)
            self.sock.close()
            return

        ack_hs = AckDatagram(0)
        self.sock.sendto(ack_hs.to_bytes(), self.client_addr)
        
        self.logger.debug(f"DownloadWorker started on port {local_port} for {self.client_addr} ({self.protocol_name})")

        if self.protocol_name == SR_STRATEGY:
            protocol = SelectiveRepeatProtocol(self.sock, self.client_addr, self.logger)
        elif self.protocol_name == SW_STRATEGY:
            protocol = StopAndWaitProtocol(self.sock, self.client_addr, self.logger)
        else:
            error_msg = f"Unsupported protocol: {self.protocol_name}"
            self.logger.error(error_msg)
            send_error_reliably(self.sock, self.client_addr, error_msg)
            self.sock.close()
            return

        try:
            final_seq = protocol.send_file(self.file_path, seq_num=1)
            self._teardown_phase(final_seq)
            self.logger.info(f"Download completed: {self.file_path}")

        except ConnectionError as e:
            self.logger.error(f"Send failure: {e}")
            send_error_reliably(self.sock, self.client_addr, f"Connection error during transfer: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {e}")
            send_error_reliably(self.sock, self.client_addr, f"Unexpected server error: {e}")
        finally:
            self.sock.close()

    def _teardown_phase(self, final_seq_num: int):
        """Envio Close, espero por ACK, luego recibo Close del cliente y ACKeo."""
        self.logger.debug("Starting download connection teardown...")
        self.sock.setblocking(False)
        close_packet = CloseDatagram(final_seq_num)
        bytes_to_send = close_packet.to_bytes()

        acked_server_close = False
        attempts = 0
        while attempts < MAX_NETWORK_ATTEMPTS:
            self.sock.sendto(bytes_to_send, self.client_addr)
            attempts += 1
            end_time = time.time() + TEARDOWN_GRACE_SECONDS
            while time.time() < end_time:
                try:
                    data, _ = self.sock.recvfrom(ACK_BUFFER_SIZE)
                    response = Datagram.from_bytes(data)
                    if isinstance(response, AckDatagram) and response.seq_num == final_seq_num:
                        self.logger.debug("Received ACK for server Close")
                        acked_server_close = True
                        break
                    elif isinstance(response, CloseDatagram):
                        # Me llega el Close del cliente antes que el ACK de mi close
                        # ACKeo el close del cliente y doy por terminado el teardown
                        ack = AckDatagram(response.seq_num)
                        self.sock.sendto(ack.to_bytes(), self.client_addr)
                        self.logger.debug("Received client Close. Sent ACK. Teardown complete.")
                        return
                    elif isinstance(response, ErrorDatagram):
                        self.logger.warning(f"Client sent error during teardown: {response.message}")
                        return
                except BlockingIOError:
                    time.sleep(0.01)

            if acked_server_close:
                break

        if not acked_server_close:
            self.logger.warning("Teardown finished due to max retries.")
            return

        # Espero por el Close del cliente y lo ACKeo. Si no llega, cierro igual.
        end_time = time.time() + TEARDOWN_GRACE_SECONDS
        while time.time() < end_time:
            try:
                data, _ = self.sock.recvfrom(ACK_BUFFER_SIZE)
                response = Datagram.from_bytes(data)
                if isinstance(response, CloseDatagram):
                    ack = AckDatagram(response.seq_num)
                    self.sock.sendto(ack.to_bytes(), self.client_addr)
                    self.logger.debug("Received client Close. Sent ACK. Teardown complete.")
                    return
            except BlockingIOError:
                time.sleep(0.01)

        self.logger.warning("Teardown finished waiting for client Close.")
