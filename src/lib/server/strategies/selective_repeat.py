from lib.server.strategies.base import ReceiverStrategy
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.constants import SOCKET_RECV_BUFFER, MAX_RAM_BUFFER_PACKETS


class SelectiveRepeatReceiver(ReceiverStrategy):
    def receive(self, temp_path: str) -> bool:
        expected_seq = 1
        out_of_order_buffer = {}
        target_file = None

        while True:
            data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
            packet = Datagram.from_bytes(data)

            if isinstance(packet, DataDatagram):
                if packet.seq_num >= (expected_seq + MAX_RAM_BUFFER_PACKETS):
                    self.logger.warning(f"RWND FULL! Dropping packet {packet.seq_num} to protect RAM.")
                    continue

                ack = AckDatagram(packet.seq_num)
                self.sock.sendto(ack.to_bytes(), self.client_addr)

                if packet.seq_num == expected_seq:
                    if target_file is None:
                        target_file = open(self.temp_path, 'wb')

                    target_file.write(packet.payload)
                    expected_seq += 1

                    while expected_seq in out_of_order_buffer:
                        target_file.write(out_of_order_buffer[expected_seq])
                        del out_of_order_buffer[expected_seq]
                        expected_seq += 1

                elif packet.seq_num > expected_seq:
                    if packet.seq_num not in out_of_order_buffer:
                        out_of_order_buffer[packet.seq_num] = packet.payload

            elif isinstance(packet, CloseDatagram):
                if target_file:
                    target_file.close()

                close_ack = AckDatagram(packet.seq_num)
                self.sock.sendto(close_ack.to_bytes(), self.client_addr)

                return True