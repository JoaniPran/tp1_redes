from lib.datagrams.datagram import Datagram

from lib.constants import OPCODE_ACK

class AckDatagram(Datagram):
    def __init__(self, seq_num: int):
        self.seq_num = seq_num

    def to_bytes(self) -> bytes:
        return self.pack_header(OPCODE_ACK, self.seq_num, 0)

    @staticmethod
    def from_bytes(data: bytes) -> 'Datagram':
        _, seq_num, _ = Datagram.unpack_header(data)
        return AckDatagram(seq_num)
