from lib.constants import OPCODE_HANDSHAKE_INIT, INITIAL_ACK_SEQ
from lib.datagrams.datagram import Datagram


class HandshakeDatagram(Datagram):
    def __init__(self, file_name: str):
        self.file_name = file_name

    def to_bytes(self) -> bytes:
        name_bytes = self.file_name.encode('utf-8')
        header = self.pack_header(OPCODE_HANDSHAKE_INIT, INITIAL_ACK_SEQ, len(name_bytes))
        return header + name_bytes

    @staticmethod
    def from_bytes(data: bytes) -> 'Datagram':
        _, _, size = Datagram.unpack_header(data)
        file_name = data[Datagram.HEADER_SIZE: Datagram.HEADER_SIZE +
                         size].decode('utf-8')
        return HandshakeDatagram(file_name)
