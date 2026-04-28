
from lib.datagrams.datagram import Datagram

from lib.constants import OPCODE_DOWNLOAD

class DownloadRequestDatagram(Datagram):
    def __init__(self, file_name: str):
        self.opcode = OPCODE_DOWNLOAD  
        self.file_name = file_name

    def to_bytes(self) -> bytes:
        name_bytes = self.file_name.encode('utf-8')
        # Usamos self.opcode en lugar del número "quemado"
        header = self.pack_header(self.opcode, 0, len(name_bytes))
        return header + name_bytes

    @staticmethod
    def from_bytes(data: bytes) -> 'DownloadRequestDatagram':
        # 1. Descomprimimos el header para saber cuánto mide el nombre
        _, _, size = Datagram.unpack_header(data)
        
        # 2. Extraemos los bytes del nombre (saltando el header)
        name_bytes = data[Datagram.HEADER_SIZE : Datagram.HEADER_SIZE + size]
        file_name = name_bytes.decode('utf-8')
        
        # 3. Retornamos la instancia
        return DownloadRequestDatagram(file_name)