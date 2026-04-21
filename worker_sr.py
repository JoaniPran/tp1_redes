import socket
import struct
import os
from constants import (
    OPCODE_ACK, OPCODE_DATA, OPCODE_EOF, HEADER_SIZE, PACKET_PAYLOAD_SIZE,
    WORKER_SOCKET_TIMEOUT, INITIAL_ACK_SEQ, TEMP_FILE_PREFIX, SOCKET_RECV_BUFFER
)

def handle_client(initial_data, client_addr):
    raw_name = initial_data[HEADER_SIZE:].decode('utf-8')
    file_name = os.path.basename(raw_name)
    temp_name = f"{TEMP_FILE_PREFIX}{client_addr[1]}_{file_name}"
    final_name = file_name
    print(f"[Worker] Iniciando descarga temporal SR: {temp_name}")

    worker_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    worker_sock.bind(('', 0))
    local_port = worker_sock.getsockname()[1]
    print(f"[Worker] Atendiendo a {client_addr} en puerto privado {local_port}")

    ack_handshake = struct.pack('!BIH', OPCODE_ACK, INITIAL_ACK_SEQ, 0)
    worker_sock.sendto(ack_handshake, client_addr)

    worker_sock.settimeout(WORKER_SOCKET_TIMEOUT)

    # Conjunto de secuencias recibidas (tracking)
    received_seqs = set()
    next_expected_seq = 1
    file = None

    try:
        while True:
            data, addr = worker_sock.recvfrom(SOCKET_RECV_BUFFER)
            if len(data) < HEADER_SIZE:
                continue

            opcode, seq, size = struct.unpack('!BIH', data[:HEADER_SIZE])

            if opcode == OPCODE_EOF:
                # EOF: consolidar archivo (pasaje a nombre final) y enviar ACK final
                if file:
                    file.close()
                    file = None

                os.replace(temp_name, final_name)

                ack_pack = struct.pack('!BIH', OPCODE_ACK, seq, 0)
                worker_sock.sendto(ack_pack, client_addr)
                print(f"[Worker] Archivo {final_name} consolidado con éxito.")
                break

            elif opcode == OPCODE_DATA:
                # Escribir directamente al disco en su offset
                payload = data[HEADER_SIZE:HEADER_SIZE + size]

                # Crear/abrir archivo si no existe
                if file is None:
                    file = open(temp_name, 'wb')

                # Calcular offset exacto usando el número de secuencia
                # seq es 1-indexed, así que el primer paquete va en offset 0
                offset = (seq - 1) * PACKET_PAYLOAD_SIZE
                
                try:
                    # Aprovechar size fijo de paquete, escribo en el offset de nro de paquete
                    file.seek(offset)
                    file.write(payload)
                    file.flush()  # Asegurar que se escriba inmediatamente
                    
                    # Registrar secuencia recibida
                    if seq not in received_seqs:
                        received_seqs.add(seq)
                    
                    # Enviar ACK DESPUÉS de escribir exitosamente
                    ack_pack = struct.pack('!BIH', OPCODE_ACK, seq, 0)
                    worker_sock.sendto(ack_pack, addr)  # Enviar a 'addr' del paquete recibido
                    
                except IOError as e:
                    print(f"[Worker-SR] ERROR escribiendo paquete {seq}: {e}")
                    # No enviar ACK si falló la escritura

    except socket.timeout:
        print(f"[Worker] ERROR: Timeout. Abortando {temp_name}")
    finally:
        if file:
            file.close()

        if not os.path.exists(final_name) and os.path.exists(temp_name):
            os.remove(temp_name)
        worker_sock.close()


