import socket
from lib.constants import PACKET_PAYLOAD_SIZE, ACK_BUFFER_SIZE
from lib.protocol_sender.base import TransferStrategy
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram


class StopAndWaitStrategy(TransferStrategy):
    def transfer(self, local_path: str, seq_num: int) -> int:
        self.logger.debug("Starting [Stop & Wait] Transfer...")
        self.sock.setblocking(True)
        self.sock.settimeout(self.timeout_limit)

        with open(local_path, "rb") as file:
            while True:
                block = file.read(PACKET_PAYLOAD_SIZE)
                if not block:
                    break

                data_packet = DataDatagram(seq_num, block)
                packet_bytes = data_packet.to_bytes()
                ack_received = False
                attempts = 0

                while not ack_received and attempts < self.max_attempts:
                    self.sock.sendto(packet_bytes, self.server_addr)
                    try:
                        data, _ = self.sock.recvfrom(ACK_BUFFER_SIZE)
                        response = Datagram.from_bytes(data)

                        if isinstance(response, AckDatagram) and response.seq_num == seq_num:
                            ack_received = True
                            seq_num += 1
                        else:
                            continue

                    except socket.timeout:
                        attempts += 1
                        self.logger.debug(f"S&W: Timeout for block {seq_num}. Retry {attempts}")

                if not ack_received:
                    raise ConnectionError(f"Connection lost while sending block {seq_num}")

        return seq_num