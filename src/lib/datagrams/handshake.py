from lib.constants import OPCODE_HANDSHAKE_INIT, INITIAL_ACK_SEQ
from lib.datagrams.datagram import Datagram
import os
import struct


class HandshakeDatagram(Datagram):
    def __init__(self, file_name: str, protocol: str = "sw", file_size: int = 0):
        self.file_name = file_name
        self.protocol = protocol
        self.file_size = file_size

    def to_bytes(self) -> bytes:
        name_bytes = self.file_name.encode('utf-8')
        payload = struct.pack('!BQ', self.protocol, self.file_size) + name_bytes
        header = self.pack_header(OPCODE_HANDSHAKE_INIT, INITIAL_ACK_SEQ, len(payload))
        return header + payload

    @staticmethod
    def from_bytes(data: bytes) -> 'Datagram':
        _, _, size = Datagram.unpack_header(data)
        payload = data[Datagram.HEADER_SIZE:Datagram.HEADER_SIZE + size]
        protocol, file_size = struct.unpack('!BQ', payload[:9])
        file_name = payload[9:].decode('utf-8')
        return HandshakeDatagram(file_name, protocol, file_size)
