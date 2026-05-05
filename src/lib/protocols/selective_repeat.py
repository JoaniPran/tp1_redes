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
    CWMD_BACKOFF, CWMD_MIN, MAX_RAM_BUFFER_PACKETS,
    RECEIVE_TIMEOUT, SR_MAX_IDLE_TIMEOUTS,
    TEARDOWN_ACK_RETRIES, TEARDOWN_GRACE_SECONDS
)


class SelectiveRepeatProtocol(RDTProtocol):
    def send_file(self, file_path: str, seq_num: int) -> int:
        self.logger.debug("Starting Selective Repeat + AIMD send")
        self.sock.setblocking(False)
        base_seq = seq_num
        inflight_packets = {}
        eof = False
        cwnd = CWMD_INITIAL
        max_cwnd = CWMD_MAX
        ack_streak = 0
        out_of_order_acks = 0

        with open(file_path, "rb") as file:
            while not eof or inflight_packets:
                readable, _, _ = select.select([self.sock], [], [], SELECT_TIMEOUT)

                if readable:
                    while True:
                        try:
                            data, _ = self.sock.recvfrom(ACK_BUFFER_SIZE)
                        except BlockingIOError:
                            break

                        if len(data) < Datagram.HEADER_SIZE:
                            continue

                        ack = Datagram.from_bytes(data)
                        if not isinstance(ack, AckDatagram):
                            continue

                        if ack.seq_num in inflight_packets:
                            if not inflight_packets[ack.seq_num]['ack']:
                                inflight_packets[ack.seq_num]['ack'] = True

                                if ack.seq_num > base_seq:
                                    out_of_order_acks += 1
                                    if out_of_order_acks >= 3:
                                        if base_seq in inflight_packets and not inflight_packets[base_seq]["ack"]:
                                            if not inflight_packets[base_seq].get("fast_retransmitted", False):
                                                self.logger.debug(f"Fast retransmit seq {base_seq}")
                                                self.sock.sendto(inflight_packets[base_seq]["data"], self.target_addr)
                                                inflight_packets[base_seq]["timestamp"] = time.time()
                                                inflight_packets[base_seq]["fast_retransmitted"] = True
                                                cwnd = max(cwnd * CWMD_BACKOFF, CWMD_MIN)
                                                self.logger.debug(f"Fast recovery: cwnd reduced to {int(cwnd)}")
                                        out_of_order_acks = 0
                                else:
                                    out_of_order_acks = 0

                                ack_streak += 1
                                if ack_streak > int(cwnd):
                                    cwnd = min(cwnd + CWMD_INCREMENT, max_cwnd)
                                    ack_streak = 0
                                    self.logger.debug(f"Window increased to {int(cwnd)}")

                                while base_seq in inflight_packets and inflight_packets[base_seq]['ack']:
                                    del inflight_packets[base_seq]
                                    base_seq += 1

                        r, _, _ = select.select([self.sock], [], [], 0)
                        if not r:
                            break

                while seq_num < base_seq + int(cwnd) and not eof:
                    block = file.read(PACKET_PAYLOAD_SIZE)
                    if not block:
                        eof = True
                        break

                    packet = DataDatagram(seq_num, block)
                    packet_bytes = packet.to_bytes()
                    inflight_packets[seq_num] = {
                        "data": packet_bytes,
                        "timestamp": time.time(),
                        "ack": False,
                        "fast_retransmitted": False
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
                        info["fast_retransmitted"] = False
                        timeout_occurred = True

                if timeout_occurred:
                    cwnd = max(cwnd * CWMD_BACKOFF, CWMD_MIN)
                    ack_streak = 0
                    self.logger.debug(f"AIMD: Congestion detected. Window reduced to {int(cwnd)}")

        return seq_num

    def receive_file(self, dest_path: str, expected_seq: int) -> bool:
        self.logger.debug("Starting Selective Repeat reception")
        self.sock.setblocking(False)
        buffer = {}
        idle_timeouts = 0
        max_idle_timeouts = SR_MAX_IDLE_TIMEOUTS

        with open(dest_path, "wb") as file:
            while True:
                readable, _, _ = select.select([self.sock], [], [], RECEIVE_TIMEOUT)
                if not readable:
                    idle_timeouts += 1
                    if idle_timeouts >= max_idle_timeouts:
                        raise ConnectionError("Reception timeout: sender inactive")
                    #  Cliente puede estar preparando el close
                    continue

                idle_timeouts = 0  # Reset on successful reception

                while True:
                    try:
                        data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                    except BlockingIOError:
                        break

                    packet = Datagram.from_bytes(data)

                    if isinstance(packet, DataDatagram):
                        if packet.seq_num < expected_seq:
                            ack = AckDatagram(packet.seq_num)
                            self.sock.sendto(ack.to_bytes(), self.target_addr)
                            continue

                        ack = AckDatagram(packet.seq_num)
                        self.sock.sendto(ack.to_bytes(), self.target_addr)

                        if packet.seq_num == expected_seq:
                            file.write(packet.payload)
                            self.logger.debug(f"Received block {packet.seq_num}")
                            expected_seq += 1
                            while expected_seq in buffer:
                                file.write(buffer.pop(expected_seq))
                                self.logger.debug(f"Received block {expected_seq - 1} (from buffer)")
                                expected_seq += 1
                        elif packet.seq_num > expected_seq:
                            if len(buffer) < MAX_RAM_BUFFER_PACKETS:
                                buffer[packet.seq_num] = packet.payload

                    elif isinstance(packet, CloseDatagram):
                        if packet.seq_num == expected_seq and not buffer:
                            ack = AckDatagram(packet.seq_num)
                            self.sock.sendto(ack.to_bytes(), self.target_addr)

                            # Aumento la seq para el Close del server y envío nuestro Close
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
                        else:
                            ack = AckDatagram(expected_seq - 1)
                            self.sock.sendto(ack.to_bytes(), self.target_addr)
                            self.logger.debug("Close received but data missing, waiting for retransmissions")

                    readable_more, _, _ = select.select([self.sock], [], [], 0)
                    if not readable_more:
                        break
