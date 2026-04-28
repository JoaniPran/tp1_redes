import time
import select
from lib.protocols.base import TransferStrategy
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram

from lib.constants import PACKET_PAYLOAD_SIZE
from lib.constants import SOCKET_RECV_BUFFER
from lib.constants import CWMD_INITIAL
from lib.constants import CWMD_MAX
from lib.constants import CWMD_MIN
from lib.constants import SELECT_TIMEOUT

class SelectiveRepeatStrategy(TransferStrategy):
    def transfer(self, local_path: str, seq_num: int) -> int:
        self.logger.debug("Starting [Selective Repeat + AIMD] Transfer...")
        self.sock.setblocking(False)

        base_seq = seq_num
        inflight_packets = {}
        eof_reached = False

        cwnd = CWMD_INITIAL
        max_cwnd = CWMD_MAX
        ack_streak = 0

        with open(local_path, "rb") as file:
            while not eof_reached or len(inflight_packets) > 0:
                readable, _, _ = select.select([self.sock], [], [], SELECT_TIMEOUT)
                if readable:
                    data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                    if len(data) >= 7:
                        ack = Datagram.from_bytes(data)

                        if isinstance(ack, AckDatagram) and ack.seq_num in inflight_packets:
                            if not inflight_packets[ack.seq_num]['ack']:
                                inflight_packets[ack.seq_num]['ack'] = True

                                ack_streak += 1
                                if ack_streak >= int(cwnd):
                                    cwnd = min(cwnd + CWMD_MIN, max_cwnd)
                                    ack_streak = 0
                                    self.logger.debug(f"AIMD: Window increased to {int(cwnd)}")

                                while base_seq in inflight_packets and inflight_packets[base_seq]['ack']:
                                    del inflight_packets[base_seq]
                                    base_seq += 1

                while seq_num < base_seq + int(cwnd) and not eof_reached:
                    block = file.read(PACKET_PAYLOAD_SIZE)
                    if not block:
                        eof_reached = True
                        break

                    data_packet = DataDatagram(seq_num, block)
                    packet_bytes = data_packet.to_bytes()

                    inflight_packets[seq_num] = {
                        "data": packet_bytes,
                        "timestamp": time.time(),
                        "ack": False
                    }

                    self.sock.sendto(packet_bytes, self.server_addr)
                    seq_num += 1

                current_time = time.time()
                timeout_occurred = False
                for current_seq, info in inflight_packets.items():
                    if not info["ack"] and (current_time - info["timestamp"] > self.timeout_limit):
                        self.logger.debug(f"SR: Timeout for seq {current_seq}. Resending...")
                        self.sock.sendto(info["data"], self.server_addr)
                        info["timestamp"] = current_time
                        timeout_occurred = True

                if timeout_occurred:
                    cwnd = max(cwnd / CWMD_INITIAL, CWMD_MIN)
                    ack_streak = 0
                    self.logger.debug(f"AIMD: Congestion detected. Window decreased to {int(cwnd)}")

        return seq_num