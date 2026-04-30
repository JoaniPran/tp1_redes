import time
import select

from lib.protocols.base import RDTProtocol
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.constants import (
    PACKET_PAYLOAD_SIZE, ACK_BUFFER_SIZE, SOCKET_RECV_BUFFER,
    SELECT_TIMEOUT, CWMD_INITIAL, CWMD_MAX, CWMD_INCREMENT,
    CWMD_BACKOFF, CWMD_MIN, MAX_RAM_BUFFER_PACKETS
)


class SelectiveRepeatProtocol(RDTProtocol):
    def send_file(self, file_path: str, seq_num: int) -> int:
        self.logger.debug("Iniciando envío con Selective Repeat + AIMD")
        self.sock.setblocking(False)
        base_seq = seq_num
        inflight_packets = {}
        eof = False
        cwnd = CWMD_INITIAL
        max_cwnd = CWMD_MAX
        ack_streak = 0

        with open(file_path, "rb") as file:
            while not eof or inflight_packets:
                readable, _, _ = select.select([self.sock], [], [], SELECT_TIMEOUT)
                if readable:
                    data, _ = self.sock.recvfrom(ACK_BUFFER_SIZE)
                    if len(data) >= Datagram.HEADER_SIZE:
                        ack = Datagram.from_bytes(data)
                        if isinstance(ack, AckDatagram) and ack.seq_num in inflight_packets:
                            if not inflight_packets[ack.seq_num]['ack']:
                                inflight_packets[ack.seq_num]['ack'] = True
                                ack_streak += 1
                                if ack_streak > int(cwnd):
                                    cwnd = min(cwnd + CWMD_INCREMENT, max_cwnd)
                                    ack_streak = 0
                                    self.logger.debug(f"Ventana incrementada a {int(cwnd)}")
                                while base_seq in inflight_packets and inflight_packets[base_seq]['ack']:
                                    del inflight_packets[base_seq]
                                    base_seq += 1

                while seq_num < base_seq + int(cwnd) and not eof:
                    block = file.read(PACKET_PAYLOAD_SIZE)
                    if not block: eof = True; break

                    packet = DataDatagram(seq_num, block)
                    packet_bytes = packet.to_bytes()
                    inflight_packets[seq_num] = {
                        "data": packet_bytes,
                        "timestamp": time.time(),
                        "ack": False
                    }
                    self.sock.sendto(packet_bytes, self.target_addr)
                    seq_num += 1

                current_time = time.time()
                timeout_occurred = False
                for current_seq, info in inflight_packets.items():
                    if not info["ack"] and (current_time - info["timestamp"] > self.timeout_limit):
                        self.logger.debug(f"SR: Timeout for seq {current_seq}. Resending...")
                        self.sock.sendto(info["data"], self.target_addr)
                        info["timestamp"] = current_time
                        timeout_occurred = True

                if timeout_occurred:
                    cwnd = max(cwnd * CWMD_BACKOFF, CWMD_MIN)
                    ack_streak = 0
                    self.logger.debug(f"AIMD: Congestion detectada. Ventana reducida a {int(cwnd)}")

        return seq_num

    def receive_file(self, dest_path: str, expected_seq: int) -> bool:
        self.logger.debug("Iniciando recepción con Selective Repeat")
        self.sock.setblocking(False)
        buffer = {}

        with open(dest_path, "wb") as file:
            while True:
                readable, _, _ = select.select([self.sock], [], [], 5.0)  # Timeout de seguridad
                if not readable: raise ConnectionError("Timeout de recepción")

                data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                packet = Datagram.from_bytes(data)

                if isinstance(packet, DataDatagram):
                    ack = AckDatagram(packet.seq_num)
                    self.sock.sendto(ack.to_bytes(), self.target_addr)

                    if packet.seq_num == expected_seq:
                        file.write(packet.payload)
                        expected_seq += 1
                        while expected_seq in buffer:
                            file.write(buffer.pop(expected_seq))
                            expected_seq += 1
                    elif packet.seq_num > expected_seq:
                        if len(buffer) < MAX_RAM_BUFFER_PACKETS:
                            buffer[packet.seq_num] = packet.payload

                elif isinstance(packet, CloseDatagram):
                    ack = AckDatagram(packet.seq_num)
                    self.sock.sendto(ack.to_bytes(), self.target_addr)
                    return True