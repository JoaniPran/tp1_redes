import socket
import time

from lib.protocols.base import RDTProtocol
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.constants import (
    PACKET_PAYLOAD_SIZE,
    ACK_BUFFER_SIZE,
    SOCKET_RECV_BUFFER,
    SW_RECEIVE_TIMEOUT,
    SW_MAX_IDLE_TIMEOUTS,
    TEARDOWN_ACK_RETRIES,
    TEARDOWN_GRACE_SECONDS,
)


class StopAndWaitProtocol(RDTProtocol):
    def send_file(self, file_path: str, seq_num: int) -> int:
        self.logger.debug(f"Sending file via Stop & Wait to {self.target_addr}")
        self.sock.settimeout(self.timeout_limit)

        with open(file_path, "rb") as file:
            while True:
                block = file.read(PACKET_PAYLOAD_SIZE)
                if not block:
                    break

                packet = DataDatagram(seq_num, block)
                packet_bytes = packet.to_bytes()

                ack_received = False
                attempts = 0
                while not ack_received and attempts < self.max_attempts:
                    self.sock.sendto(packet_bytes, self.target_addr)
                    try:
                        data, _ = self.sock.recvfrom(ACK_BUFFER_SIZE)
                        response = Datagram.from_bytes(data)
                        if isinstance(response, AckDatagram) and response.seq_num == seq_num:
                            ack_received = True
                            self.logger.debug(f"Block {seq_num} acknowledged.")
                            seq_num += 1
                    except socket.timeout:
                        attempts += 1
                if not ack_received:
                    raise ConnectionError(f"Max retries reached for block {seq_num}")
            return seq_num

    def receive_file(self, dest_path: str, expected_seq: int) -> bool:
        self.logger.debug(f"Receiving file via Stop & Wait from {self.target_addr}")
        self.sock.settimeout(SW_RECEIVE_TIMEOUT)
        idle_timeouts = 0
        max_idle_timeouts = SW_MAX_IDLE_TIMEOUTS

        with open(dest_path, "wb") as file:
            while True:
                try:
                    data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                    idle_timeouts = 0  # Reset si recibo algo
                    packet = Datagram.from_bytes(data)

                    if isinstance(packet, DataDatagram):
                        if packet.seq_num == expected_seq:
                            file.write(packet.payload)
                            self.logger.debug(f"Received block {packet.seq_num}")
                            expected_seq += 1
                            ack = AckDatagram(packet.seq_num)
                            self.sock.sendto(ack.to_bytes(), self.target_addr)
                        else:
                            ack = AckDatagram(expected_seq - 1)
                            self.sock.sendto(ack.to_bytes(), self.target_addr)

                    elif isinstance(packet, CloseDatagram):
                        # ACK del Close del cliente, luego envío nuestro Close con el siguiente seq y espero su ACK
                        self.final_seq_received = packet.seq_num
                        ack = AckDatagram(packet.seq_num)
                        self.sock.sendto(ack.to_bytes(), self.target_addr)
                        expected_seq += 1
                        server_close = CloseDatagram(expected_seq)
                        self.sock.setblocking(False)
                        for attempt in range(TEARDOWN_ACK_RETRIES):
                            self.sock.sendto(server_close.to_bytes(), self.target_addr)
                            end_time = time.time() + TEARDOWN_GRACE_SECONDS
                            while time.time() < end_time:
                                try:
                                    data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                                    pkt = Datagram.from_bytes(data)
                                    if isinstance(pkt, AckDatagram) and pkt.seq_num == expected_seq:
                                        self.logger.debug("Received ACK for server FIN")
                                        return True
                                except BlockingIOError:
                                    time.sleep(0.01)
                        return True
                except socket.timeout:
                    idle_timeouts += 1
                    if idle_timeouts >= max_idle_timeouts:
                        raise ConnectionError("Sender inactivity timeout")
                    # Puede estar preparando el close, sigo esperando
