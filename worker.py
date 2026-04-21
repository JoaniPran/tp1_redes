import os
import socket
import struct
from constants import (
    OPCODE_ACK, OPCODE_DATA, OPCODE_EOF, HEADER_SIZE,
    WORKER_SOCKET_TIMEOUT, INITIAL_ACK_SEQ, TEMP_FILE_PREFIX
)

def handle_client(initial_data, client_addr):
    raw_name = initial_data[HEADER_SIZE:].decode('utf-8')
    file_name = os.path.basename(raw_name)
    temp_name = f"{TEMP_FILE_PREFIX}{client_addr[1]}_{file_name}"
    final_name = file_name
    print(f"[Worker] Iniciando descarga temporal: {temp_name}")

    worker_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    worker_sock.bind(('', 0))
    local_port = worker_sock.getsockname()[1]
    print(f"[Worker] Atendiendo a {client_addr} en puerto privado {local_port}")

    ack_handshake = struct.pack('!BIH', OPCODE_ACK, INITIAL_ACK_SEQ, 0)
    worker_sock.sendto(ack_handshake, client_addr)

    worker_sock.settimeout(WORKER_SOCKET_TIMEOUT)
    expected_sequence = 1

    file = None

    try:
        while True:
            data, addr = worker_sock.recvfrom(2048)
            if len(data) < HEADER_SIZE:
                continue

            opcode, seq, size = struct.unpack('!BIH', data[:HEADER_SIZE])

            if opcode == OPCODE_EOF:
                if file:
                    file.close()
                    file = None

                os.replace(temp_name, final_name)

                ack_pack = struct.pack('!BIH', OPCODE_ACK, seq, 0)
                worker_sock.sendto(ack_pack, client_addr)
                print(f"[Worker] Transaccion exitosa. Archivo {final_name} consolidado.")
                break

            elif opcode == OPCODE_DATA:
                if seq == expected_sequence:
                    if file is None:
                        file = open(temp_name, 'wb')

                    payload = data[HEADER_SIZE:HEADER_SIZE + size]
                    file.write(payload)

                    ack_pack = struct.pack('!BIH', OPCODE_ACK, expected_sequence, 0)
                    worker_sock.sendto(ack_pack, client_addr)
                    expected_sequence += 1

                elif seq < expected_sequence:
                    print(f"[Worker] Duplicado seq={seq} detectado. Reenviando ACK...")
                    ack_pack = struct.pack('!BIH', OPCODE_ACK, seq, 0)
                    worker_sock.sendto(ack_pack, client_addr)


    except socket.timeout:
        print(f"[Worker] ERROR: El cliente {client_addr} desaparecio (Timeout).")
    finally:
        if file:
            file.close()
        if not os.path.exists(final_name) and os.path.exists(temp_name):
            os.remove(temp_name)
        worker_sock.close()
        print(f"[Worker] Conexion privada cerrada con {client_addr}")