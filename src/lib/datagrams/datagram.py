import struct

from abc import ABC, abstractmethod
from lib.constants import (
    OPCODE_HANDSHAKE_INIT, OPCODE_DATA, OPCODE_ACK, OPCODE_EOF
)


class Datagram(ABC):
    HEADER_FORMAT = '!BIH'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    @staticmethod
    def pack_header(opcode: int, seq_num: int, payload_size: int) -> bytes:
        return struct.pack(Datagram.HEADER_FORMAT,
                           opcode, seq_num, payload_size)

    @staticmethod
    def unpack_header(data: bytes):
        return struct.unpack(Datagram.HEADER_FORMAT, data[:Datagram.HEADER_SIZE])

    @abstractmethod
    def to_bytes(self) -> bytes:
        pass

    @staticmethod
    def from_bytes(data: bytes) -> 'Datagram':
        if len(data) < Datagram.HEADER_SIZE:
            raise ValueError("Datagram is too short")

        opcode = data[0]

        if opcode == OPCODE_HANDSHAKE_INIT:
            from lib.datagrams.handshake import HandshakeDatagram
            return HandshakeDatagram.from_bytes(data)
        elif opcode == OPCODE_DATA:
            from lib.datagrams.data import DataDatagram
            return DataDatagram.from_bytes(data)
        elif opcode == OPCODE_ACK:
            from lib.datagrams.ack import AckDatagram
            return AckDatagram.from_bytes(data)
        elif opcode == OPCODE_EOF:
            from lib.datagrams.close import CloseDatagram
            return CloseDatagram.from_bytes(data)
        else:
            raise ValueError("Unknown opcode")
