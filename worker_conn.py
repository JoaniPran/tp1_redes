import socket
import struct

def handle_client(initial_data, client_addr):
    file_name = initial_data[7:].decode('utf-8')
    save_name = f"recv_{file_name}"
    print(f"[Worker] Iniciando descarga: {file_name} -> guardando como {save_name}")

    worker_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    worker_sock.bind(('', 0))
    local_port = worker_sock.getsockname()[1]
    print(f"[Worker] Atendiendo a {client_addr} en puerto privado {local_port}")

    ack_handshake = struct.pack('!BIH', 3, 0, 0)
    worker_sock.sendto(ack_handshake, client_addr)

    # worker_sock.settimeout(10)
    expected_sequence = 1

    try:
        with open(save_name, 'wb') as file:
            while True:
                data, addr = worker_sock.recvfrom(1024)

                if len(data) < 7:
                    continue

                opcode, seq, size = struct.unpack('!BIH', data[:7])

                if opcode == 7:
                    print(f"[Worker] Archivo {save_name} recibido con exito.")
                    break

                elif opcode == 2:
                    if seq == expected_sequence:
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
        worker_sock.close()
        print(f"[Worker] Conexion privada cerrada con {client_addr}")