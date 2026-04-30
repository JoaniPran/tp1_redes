import socket

from lib.protocols.base import RDTProtocol
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.constants import PACKET_PAYLOAD_SIZE, ACK_BUFFER_SIZE, SOCKET_RECV_BUFFER, WORKER_SOCKET_TIMEOUT


class StopAndWaitProtocol(RDTProtocol):
    def send_file(self, file_path: str, seq_num: int) -> int:
        self.logger.debug(f"Enviando archivo por Stop & Wait a {self.target_addr}")
        self.sock.settimeout(self.timeout_limit)

        with open(file_path, "rb") as file:
            while True:
                block = file.read(PACKET_PAYLOAD_SIZE)
                if not block: break

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
                            seq_num += 1
                    except socket.timeout:
                        attempts += 1
                if not ack_received:
                    raise ConnectionError(f"Límite de reintentos alcanzado en bloque {seq_num}")
            return seq_num

    def receive_file(self, dest_path: str, expected_seq: int) -> bool:
        self.logger.debug(f"Recibiendo archivo por Stop & Wait de {self.target_addr}")
        self.sock.settimeout(WORKER_SOCKET_TIMEOUT)

        with open(dest_path, "wb") as file:
            while True:
                try:
                    data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                    packet = Datagram.from_bytes(data)

                    if isinstance(packet, DataDatagram):
                        if packet.seq_num == expected_seq:
                            file.write(packet.payload)
                            expected_seq += 1

                        ack = AckDatagram(packet.seq_num)
                        self.sock.sendto(ack.to_bytes(), self.target_addr)

                    elif isinstance(packet, CloseDatagram):
                        ack = AckDatagram(packet.seq_num)
                        self.sock.sendto(ack.to_bytes(), self.target_addr)
                        return True
                except socket.timeout:
                    raise ConnectionError("Inactividad prolongada del emisor.")