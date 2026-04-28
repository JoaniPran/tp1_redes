import socket
from lib.protocols.base import TransferStrategy
from lib.datagrams.datagram import Datagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram

from lib.constants import PACKET_PAYLOAD_SIZE
from lib.constants import SOCKET_RECV_BUFFER

class StopAndWaitStrategy(TransferStrategy):
    def transfer(self, local_path: str, seq_num: int) -> int:
        self.logger.debug("Starting [Stop & Wait] Transfer...")
        self.sock.setblocking(True)
        self.sock.settimeout(self.timeout_limit)

        with open(local_path, "rb") as file:
            while True:
                block = file.read(PACKET_PAYLOAD_SIZE)
                if not block:
                    break

                data_packet = DataDatagram(seq_num, block)
                packet_bytes = data_packet.to_bytes()
                ack_received = False
                attempts = 0

                while not ack_received and attempts < self.max_attempts:
                    self.sock.sendto(packet_bytes, self.server_addr)
                    try:
                        data, _ = self.sock.recvfrom(PACKET_PAYLOAD_SIZE)
                        response = Datagram.from_bytes(data)

                        if isinstance(response, AckDatagram) and response.seq_num == seq_num:
                            ack_received = True
                            seq_num += 1
                        else:
                            continue

                    except socket.timeout:
                        attempts += 1
                        self.logger.debug(f"S&W: Timeout for block {seq_num}. Retry {attempts}")

                if not ack_received:
                    raise ConnectionError(f"Connection lost while sending block {seq_num}")

        return seq_num
    
    def receive(self, local_path: str):
        self.logger.debug("Iniciando recepción [Stop & Wait]...")
        self.sock.settimeout(self.timeout_limit)
        
        expected_seq = 1
        # Abrimos el archivo local para escribir los bytes que nos mande el server
        with open(local_path, "wb") as file:
            while True:
                try:
                    # 1. Esperar el paquete de datos del servidor (Worker)
                    data, addr = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                    packet = Datagram.from_bytes(data)

                    # 2. ¿Es un paquete de datos (Opcode 2)?
                    if isinstance(packet, DataDatagram):
                        if packet.seq_num == expected_seq:
                            # Escribimos en el disco lo que llegó en el payload
                            file.write(packet.payload)
                            
                            # Enviamos ACK del paquete recibido
                            ack = AckDatagram(packet.seq_num)
                            self.sock.sendto(ack.to_bytes(), self.server_addr)
                            
                            expected_seq += 1
                        else:
                            # Si llega un seq_num viejo, reenviamos el ACK anterior
                            # (El server no recibió nuestro ACK anterior)
                            ack = AckDatagram(packet.seq_num)
                            self.sock.sendto(ack.to_bytes(), self.server_addr)

                    # 3. ¿Es el fin de la transferencia (Opcode 7)?
                    elif isinstance(packet, CloseDatagram):
                        # Enviamos el último ACK para que el server cierre tranquilo
                        close_ack = AckDatagram(packet.seq_num)
                        self.sock.sendto(close_ack.to_bytes(), self.server_addr)
                        self.logger.debug("Paquete de cierre recibido. Descarga finalizada.")
                        break # Salimos del bucle, el archivo está completo

                except socket.timeout:
                    self.logger.error("Timeout: El servidor dejó de enviar datos.")
                    raise ConnectionError("Servidor inactivo durante la descarga.")