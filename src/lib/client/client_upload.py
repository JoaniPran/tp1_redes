import socket
import os
import time

from lib.datagrams.datagram import Datagram
from lib.datagrams.handshake import HandshakeDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.datagrams.error import ErrorDatagram
from lib.protocols.stop_and_wait import StopAndWaitProtocol
from lib.protocols.selective_repeat import SelectiveRepeatProtocol
from lib.client.base_client import ClientStrategy
from lib.constants import MAX_FILE_SIZE, PACKET_PAYLOAD_SIZE, SOCKET_RECV_BUFFER, SW_STRATEGY, SR_STRATEGY, HANDSHAKE_TIMEOUT, TEARDOWN_TIMEOUT, TEARDOWN_ACK_RETRIES, TEARDOWN_ACK_SLEEP, TEARDOWN_GRACE_SECONDS, CLIENT_TEARDOWN_TOTAL_ATTEMPTS


class ClientUploader(ClientStrategy):
    def upload_file(self, local_path: str, remote_name: str):
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"Local file {local_path} does not exist.")
        if not os.access(local_path, os.R_OK):
            raise PermissionError(f"No read permission for {local_path}.")

        file_size = os.path.getsize(local_path)
        if file_size > MAX_FILE_SIZE:
            self.logger.error(f"File size ({file_size} bytes) exceeds the 20MB limit.")
            raise ValueError(f"File size exceeds the maximum allowed size of {MAX_FILE_SIZE} bytes.")
        self._handshake_phase(remote_name, file_size)

        if self.protocol_name == SR_STRATEGY:
            protocol = SelectiveRepeatProtocol(self.sock, self.server_addr, self.logger)
        elif self.protocol_name == SW_STRATEGY:
            protocol = StopAndWaitProtocol(self.sock, self.server_addr, self.logger)
        else:
            raise ValueError(f"Protocol '{self.protocol_name}' not supported.")

        self.next_seq_num = protocol.send_file(local_path, self.next_seq_num)
        self._teardown_phase()
        self.sock.close()

    def _handshake_phase(self, remote_name: str, file_size: int):
        self.logger.debug("Starting handshake...")
        self.sock.settimeout(HANDSHAKE_TIMEOUT)

        hs_packet = HandshakeDatagram(remote_name, self.protocol_name, file_size)
        bytes_to_send = hs_packet.to_bytes()

        attempts = 0
        while attempts < self.max_attempts:
            self.sock.sendto(bytes_to_send, self.server_addr)
            try:
                data, new_addr = self.sock.recvfrom(PACKET_PAYLOAD_SIZE)
                response = Datagram.from_bytes(data)

                if isinstance(response, ErrorDatagram):
                    self.logger.error(f"Server rejected upload: {response.message}")
                    raise ConnectionError(f"Server error: {response.message}")

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
        # Envio el Close un par de veces 
        close_packet = CloseDatagram(self.next_seq_num)
        close_bytes = close_packet.to_bytes()

        for _ in range(TEARDOWN_ACK_RETRIES):
            self.sock.sendto(close_bytes, self.server_addr)
            time.sleep(TEARDOWN_ACK_SLEEP)

        # Espero el ACK del Close, si no llega, cierro igual
        deadline = time.time() + TEARDOWN_GRACE_SECONDS
        ack_received = False
        self.sock.settimeout(TEARDOWN_ACK_SLEEP)
        while time.time() < deadline:
            try:
                data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
            except socket.timeout:
                continue
            try:
                pkt = Datagram.from_bytes(data)
            except Exception:
                continue

            if isinstance(pkt, AckDatagram) and pkt.seq_num == self.next_seq_num:
                ack_received = True
                self.logger.debug(f"Received ACK for client FIN (seq={pkt.seq_num})")
                continue

            if isinstance(pkt, CloseDatagram):
                ack = AckDatagram(pkt.seq_num)
                self.sock.sendto(ack.to_bytes(), self.server_addr)
                self.logger.debug(f"Sent ACK for server FIN (seq={pkt.seq_num}). Teardown complete.")
                return

            if isinstance(pkt, ErrorDatagram):
                self.logger.warning(f"Client sent error during teardown: {pkt.message}")
                return

        if ack_received:
            self.logger.debug("Client FIN acknowledged; teardown complete.")
        else:
            self.logger.debug("No ACK or server FIN received; teardown complete.")