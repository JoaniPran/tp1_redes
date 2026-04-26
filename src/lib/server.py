import socket
import threading
import os
import logging

from lib.datagrams.datagram import Datagram
from lib.datagrams.handshake import HandshakeDatagram
from lib.datagrams.data import DataDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.close import CloseDatagram
from lib.datagrams.donwload import DownloadRequestDatagram
from lib.downloadWorker import DownloadWorker


class ServerDispatcher:
    def __init__(self, host: str, port: int, storage: str, logger: logging.Logger):
        self.addr = (host, port)
        self.storage = storage
        self.logger = logger
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Crea un socket UDP, SOCK_DGRAM->UDP, INET se refiere a IPv4,  guardamos la familiade los ips que podemos utulizar y el protocolo de la coneccion que vamos a hacer 

        os.makedirs(self.storage, exist_ok=True)

    def start(self):
        self.sock.bind(self.addr) # pone el servidor a escuchar en
        self.logger.info(f"Dispatcher listening on {self.addr}. Storage: {self.storage}")

        while True:
            data, client_addr = self.sock.recvfrom(2048) #El servidor se queda "congelado" en esta línea hasta que llegue un paquete UDP. El 2048 es el tamaño máximo de bytes que está dispuesto a recibir de un solo golpe (el buffer).
            try:
                packet = Datagram.from_bytes(data)
                """Data: Son los bytes puros (binario) que envió el cliente. Es información "cruda", 
                el servidor aún no sabe qué significan.
                client_addr: Es una tupla (IP, Puerto) del cliente. Esto es fundamental 
                en UDP porque, como no hay una conexión fija, el servidor 
                necesita esta dirección para saber a quién responderle después."""

                if isinstance(packet, HandshakeDatagram):
                    self.logger.info(f"New Handshake from {client_addr} for file: {packet.file_name}")
                    worker = Worker(client_addr, packet.file_name, self.storage, self.logger)
                    worker_thread = threading.Thread(target=worker.run)
                    worker_thread.daemon = True                 
                    worker_thread.start()
                elif isinstance(packet, DownloadRequestDatagram):
                    self.logger.info(f"Descarga detectada desde {client_addr} para {packet.file_name}")
                    # Lanzamos el nuevo worker que creamos antes
                    worker = DownloadWorker(client_addr, packet.file_name, self.storage, self.logger)
                    worker_thread = threading.Thread(target=worker.run)
                    worker_thread.daemon = True
                    worker_thread.start()
                else:
                    self.logger.warning(f"Ignored packet on port {self.addr}: Unexpected Opcode.")

            except Exception as e:
                self.logger.debug(f"Garbage received or error parsing datagram: {e}")


class Worker:
    def __init__(self, client_addr: tuple, file_name: str, storage: str, logger: logging.Logger):
        self.client_addr = client_addr
        self.logger = logger

        safe_name = os.path.basename(file_name)
        self.final_path = os.path.join(storage, safe_name)
        self.temp_path = os.path.join(storage, f".tmp_{client_addr[1]}_{safe_name}")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))     
        """Worker: Se crea y hace self.sock.bind(('', 0)). 
        Ese 0 le dice al Sistema Operativo: 
        "Dame cualquier puerto que esté libre" (ejemplo: el 54321)."""
        self.sock.settimeout(15.0)

    def run(self):
        local_port = self.sock.getsockname()[1]
        self.logger.debug(f"Worker started on port {local_port} for client {self.client_addr}")

        ack_hs = AckDatagram(0)
        self.sock.sendto(ack_hs.to_bytes(), self.client_addr)

        expected_seq = 1
        out_of_order_buffer = {}
        target_file = None

        try:
            while True:
                data, _ = self.sock.recvfrom(2048)
                packet = Datagram.from_bytes(data)

                if isinstance(packet, DataDatagram):
                    ack = AckDatagram(packet.seq_num)
                    self.sock.sendto(ack.to_bytes(), self.client_addr)

                    if packet.seq_num == expected_seq:
                        if target_file is None:
                            target_file = open(self.temp_path, 'wb')

                        target_file.write(packet.payload)
                        expected_seq += 1

                        while expected_seq in out_of_order_buffer:
                            target_file.write(out_of_order_buffer[expected_seq])
                            del out_of_order_buffer[expected_seq]
                            expected_seq += 1

                    elif packet.seq_num > expected_seq:
                        if packet.seq_num not in out_of_order_buffer:
                            out_of_order_buffer[packet.seq_num] = packet.payload

                elif isinstance(packet, CloseDatagram):
                    if target_file:
                        target_file.close()
                        target_file = None

                    os.replace(self.temp_path, self.final_path)

                    close_ack = AckDatagram(packet.seq_num)
                    self.sock.sendto(close_ack.to_bytes(), self.client_addr)
                    self.logger.info(f"File successfully consolidated at: {self.final_path}")
                    break

        except socket.timeout:
            self.logger.error(f"Worker {local_port} died due to inactivity.")
        except Exception as e:
            self.logger.error(f"Error in Worker {local_port}: {e}")
        finally:
            if target_file:
                target_file.close()
            if not os.path.exists(self.final_path) and os.path.exists(self.temp_path):
                os.remove(self.temp_path)
            self.sock.close()