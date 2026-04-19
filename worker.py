import os
import socket
import struct

def handle_client(initial_data, client_addr):
    raw_name = initial_data[7:].decode('utf-8')
    file_name = os.path.basename(raw_name)
    temp_name = f".tmp_{client_addr[1]}_{file_name}"
    final_name = file_name
    print(f"[Worker] Iniciando descarga temporal: {temp_name}")

    worker_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    worker_sock.bind(('', 0))
    local_port = worker_sock.getsockname()[1]
    print(f"[Worker] Atendiendo a {client_addr} en puerto privado {local_port}")

    ack_handshake = struct.pack('!BIH', 3, 0, 0)
    worker_sock.sendto(ack_handshake, client_addr)

    worker_sock.settimeout(10.0)
    expected_sequence = 1

    file = None

    try:
        while True:
            data, addr = worker_sock.recvfrom(2048)
            if len(data) < 7:
                continue

            opcode, seq, size = struct.unpack('!BIH', data[:7])

            if opcode == 7:
                if file:
                    file.close()
                    file = None

                os.replace(temp_name, final_name)

                ack_pack = struct.pack('!BIH', 3, seq, 0)
                worker_sock.sendto(ack_pack, client_addr)
                print(f"[Worker] Transaccion exitosa. Archivo {final_name} consolidado.")
                break

            elif opcode == 2:
                if seq == expected_sequence:
                    if file is None:
                        file = open(temp_name, 'wb')

                    payload = data[7:7 + size]
                    file.write(payload)

                    ack_pack = struct.pack('!BIH', 3, expected_sequence, 0)
                    worker_sock.sendto(ack_pack, client_addr)
                    expected_sequence += 1

                elif seq < expected_sequence:
                    print(f"[Worker] Duplicado seq={seq} detectado. Reenviando ACK...")
                    ack_pack = struct.pack('!BIH', 3, seq, 0)
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