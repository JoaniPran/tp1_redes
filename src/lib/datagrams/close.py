from lib.datagrams.datagram import Datagram

from lib.constants import OPCODE_CLOSE

class CloseDatagram(Datagram):
    def __init__(self, seq_num: int):
        self.seq_num = seq_num

    def to_bytes(self) -> bytes:
        return self.pack_header(OPCODE_CLOSE, self.seq_num, 0)

    @staticmethod
    def from_bytes(data: bytes) -> 'Datagram':
        _, seq_num, _ = Datagram.unpack_header(data)
        return CloseDatagram(seq_num)
