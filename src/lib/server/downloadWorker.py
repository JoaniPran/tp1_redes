import os
import logging
from lib.datagrams.ack import AckDatagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.close import CloseDatagram
from lib.datagrams.datagram import Datagram
import socket

class DownloadWorker:
    def __init__(self, client_addr: tuple, file_name: str, storage: str, logger: logging.Logger):
        self.client_addr = client_addr
        self.logger = logger
        self.file_path = os.path.join(storage, os.path.basename(file_name))
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0)) # Puerto aleatorio
        self.sock.settimeout(5.0)
        self.max_attempts = 5

    def run(self):
        local_port = self.sock.getsockname()[1]
        
        # 1. Verificar si el archivo existe antes de empezar
        if not os.path.exists(self.file_path):
            self.logger.error(f"Archivo no encontrado: {self.file_path}")
            # Aquí podrías enviar un paquete de error al cliente
            self.sock.close()
            return

        # 2. Primer paso: Confirmar el Handshake (Opcode 1 -> Ack 0)
        # Esto le dice al cliente el puerto del Worker y que el archivo existe
        ack_hs = AckDatagram(0)
        self.sock.sendto(ack_hs.to_bytes(), self.client_addr)

        self.logger.debug(f"DownloadWorker iniciado en puerto {local_port} enviando {self.file_path}")

        seq_num = 1
        try:
            with open(self.file_path, "rb") as f:
                while True:
                    block = f.read(1024)
                    if not block:
                        break  # Fin del archivo

                    # 3. Enviar bloque y esperar ACK (Lógica Stop & Wait)
                    data_packet = DataDatagram(seq_num, block)
                    packet_bytes = data_packet.to_bytes()
                    
                    ack_received = False
                    attempts = 0
                    
                    while not ack_received and attempts < self.max_attempts:
                        self.sock.sendto(packet_bytes, self.client_addr)
                        try:
                            data, _ = self.sock.recvfrom(1024)
                            response = Datagram.from_bytes(data)

                            if isinstance(response, AckDatagram) and response.seq_num == seq_num:
                                ack_received = True
                                seq_num += 1
                        except socket.timeout:
                            attempts += 1
                            self.logger.debug(f"Timeout en bloque {seq_num}. Reintento {attempts}")

                    if not ack_received:
                        raise ConnectionError(f"Cliente {self.client_addr} desconectado")

            # 4. Fase de Cierre: Enviar CloseDatagram (Opcode 7)
            close_packet = CloseDatagram(seq_num)
            self.sock.sendto(close_packet.to_bytes(), self.client_addr)
            self.logger.info(f"Envío de '{self.file_path}' completado con éxito.")

        except Exception as e:
            self.logger.error(f"Error en DownloadWorker: {e}")
        finally:
            self.sock.close()