import time
import select
from lib.protocols.base import TransferStrategy
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram


class SelectiveRepeatStrategy(TransferStrategy):
    def transfer(self, local_path: str, seq_num: int) -> int:
        self.logger.debug("Starting [Selective Repeat + AIMD] Transfer...")
        self.sock.setblocking(False)

        base_seq = seq_num
        inflight_packets = {}
        eof_reached = False

        cwnd = 2.0
        max_cwnd = 20.0
        ack_streak = 0

        with open(local_path, "rb") as file:
            while not eof_reached or len(inflight_packets) > 0:
                readable, _, _ = select.select([self.sock], [], [], 0.01)
                if readable:
                    data, _ = self.sock.recvfrom(2048)
                    if len(data) >= 7:
                        ack = Datagram.from_bytes(data)

                        if isinstance(ack, AckDatagram) and ack.seq_num in inflight_packets:
                            if not inflight_packets[ack.seq_num]['ack']:
                                inflight_packets[ack.seq_num]['ack'] = True

                                ack_streak += 1
                                if ack_streak >= int(cwnd):
                                    cwnd = min(cwnd + 1.0, max_cwnd)
                                    ack_streak = 0
                                    self.logger.debug(f"AIMD: Window increased to {int(cwnd)}")

                                while base_seq in inflight_packets and inflight_packets[base_seq]['ack']:
                                    del inflight_packets[base_seq]
                                    base_seq += 1

                while seq_num < base_seq + int(cwnd) and not eof_reached:
                    block = file.read(1024)
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
                    cwnd = max(cwnd / 2.0, 1.0)
                    ack_streak = 0
                    self.logger.debug(f"AIMD: Congestion detected. Window decreased to {int(cwnd)}")

        return seq_num