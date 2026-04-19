import socket
import struct
import os

def handle_client(initial_data, client_addr):
    raw_name = initial_data[7:].decode('utf-8')
    file_name = os.path.basename(raw_name)
    temp_name = f".tmp_{client_addr[1]}_{file_name}"
    final_name = file_name
    print(f"[Worker] Iniciando descarga temporal SR: {temp_name}")

    worker_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    worker_sock.bind(('', 0))
    local_port = worker_sock.getsockname()[1]
    print(f"[Worker] Atendiendo a {client_addr} en puerto privado {local_port}")

    ack_handshake = struct.pack('!BIH', 3, 0, 0)
    worker_sock.sendto(ack_handshake, client_addr)

    worker_sock.settimeout(10.0)

    expected_seq = 1
    buffer_desorden = {}
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
                print(f"[Worker] Archivo {final_name} consolidado con éxito.")
                break

            elif opcode == 2:
                ack_pack = struct.pack('!BIH', 3, seq, 0)
                worker_sock.sendto(ack_pack, client_addr)

                payload = data[7:7 + size]

                if seq == expected_seq:
                    if file is None:
                        file = open(temp_name, 'wb')

                    file.write(payload)
                    expected_seq += 1

                    while expected_seq in buffer_desorden:
                        file.write(buffer_desorden[expected_seq])
                        del buffer_desorden[expected_seq]
                        expected_seq += 1

                elif seq > expected_seq:
                    if seq not in buffer_desorden:
                        buffer_desorden[seq] = payload
                        print(f"[Worker] Paquete {seq} adelantado. Guardado en buffer de desorden.")

                else:
                    pass

    except socket.timeout:
        print(f"[Worker] ERROR: Timeout. Abortando {temp_name}")
    finally:
        if file:
            file.close()

        if not os.path.exists(final_name) and os.path.exists(temp_name):
            os.remove(temp_name)
        worker_sock.close()


