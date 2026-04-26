from lib.datagrams.datagram import Datagram
from lib.constants import OPCODE_HANDSHAKE

class HandshakeDatagram(Datagram):
    def __init__(self, file_name: str, protocol: str = "sw", file_size: int = 0):
        self.file_name = file_name
        self.protocol = protocol
        self.file_size = file_size

    def to_bytes(self) -> bytes:
        payload_str = f"{self.protocol}|{self.file_size}|{self.file_name}"
        payload_bytes = payload_str.encode('utf-8')
        header = self.pack_header(OPCODE_HANDSHAKE, 0, len(payload_bytes))
        return header + payload_bytes

    @staticmethod
    def from_bytes(data: bytes) -> 'Datagram':
        _, _, size = Datagram.unpack_header(data)
        payload = data[Datagram.HEADER_SIZE: Datagram.HEADER_SIZE +
                         size].decode('utf-8')
        parts = payload.split("|", 2)
        if len(parts) < 3:
            raise ValueError("Invalid Handshake payload format")

        return HandshakeDatagram(
            protocol=parts[0],
            file_size=int(parts[1]),
            file_name=parts[2]
        )
