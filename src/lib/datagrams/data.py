from lib.datagrams.datagram import Datagram


class DataDatagram(Datagram):
    def __init__(self, seq_num: int, payload: bytes):
        self.seq_num = seq_num
        self.payload = payload

    def to_bytes(self) -> bytes:
        header = Datagram.pack_header(2, self.seq_num, len(self.payload))
        return header + self.payload    #recibe estructura binaria

    @staticmethod
    def from_bytes(data: bytes) -> 'Datagram':
        _, seq_num, size = Datagram.unpack_header(data)
        payload = data[Datagram.HEADER_SIZE: Datagram.HEADER_SIZE + size]
        return DataDatagram(seq_num, payload)
