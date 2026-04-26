from lib.server.strategies.base import ReceiverStrategy
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.constants import SOCKET_RECV_BUFFER


class StopAndWaitReceiver(ReceiverStrategy):
    def receive(self, temp_path: str) -> bool:
        expected_seq = 1
        target_file = None

        while True:
            data, _ = self.sock.recvfrom(SOCKET_RECV_BUFFER)
            packet = Datagram.from_bytes(data)

            if isinstance(packet, DataDatagram):
                if packet.seq_num == expected_seq:
                    if target_file is None:
                        target_file = open(temp_path, 'wb')

                    target_file.write(packet.payload)
                    expected_seq += 1

                    ack = AckDatagram(packet.seq_num)
                    self.sock.sendto(ack.to_bytes(), self.client_addr)

                elif packet.seq_num < expected_seq:
                    ack = AckDatagram(packet.seq_num)
                    self.sock.sendto(ack.to_bytes(), self.client_addr)

            elif isinstance(packet, CloseDatagram):
                if target_file:
                    target_file.close()

                close_ack = AckDatagram(packet.seq_num)
                self.sock.sendto(close_ack.to_bytes(), self.client_addr)

                return True