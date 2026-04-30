from lib.datagrams.datagram import Datagram
from lib.constants import OPCODE_DOWNLOAD


class DownloadRequestDatagram(Datagram):
    def __init__(self, file_name: str, protocol: str = "sw"):
        self.opcode = OPCODE_DOWNLOAD  
        self.file_name = file_name
        self.protocol = protocol

    def to_bytes(self) -> bytes:
        payload_str = f"{self.protocol}|{self.file_name}"
        payload_bytes = payload_str.encode('utf-8')
        header = self.pack_header(self.opcode, 0, len(payload_bytes))
        return header + payload_bytes

    @staticmethod
    def from_bytes(data: bytes) -> 'DownloadRequestDatagram':
        _, _, size = Datagram.unpack_header(data)

        name_bytes = data[Datagram.HEADER_SIZE: Datagram.HEADER_SIZE + size]
        payload_str = name_bytes.decode('utf-8')

        parts = payload_str.split("|", 1)
        if len(parts) < 2:
            raise ValueError("Invalid DownloadRequest format")
        return DownloadRequestDatagram(file_name=parts[1], protocol=parts[0])