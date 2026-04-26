from lib.datagrams.datagram import Datagram

class ErrorDatagram(Datagram):
    def __init__(self, message: str):
        self.message = message

    def to_bytes(self) -> bytes:
        message_bytes = self.message.encode('utf-8')
        header = self.pack_header(4, 0, len(message_bytes))
        return header + message_bytes

    @staticmethod
    def from_bytes(data: bytes) -> 'ErrorDatagram':
        _, _, size = Datagram.unpack_header(data)
        message = data[Datagram.HEADER_SIZE: Datagram.HEADER_SIZE + size].decode('utf-8')
        return ErrorDatagram(message)