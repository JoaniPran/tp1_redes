import socket
import struct
import sys
import time
import select
import argparse
import os

def start_upload(server_ip, server_port, file_name):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (server_ip, server_port)

    nombre_limpio = os.path.basename(file_name)

    header = struct.pack('!BIH', 0, 0, len(file_name))
    ack_received = False
    attempts = 0
    max_attempts = 25
    client_socket.settimeout(0.2)

    while not ack_received and attempts < max_attempts:
        client_socket.sendto(header + nombre_limpio.encode('utf-8'), server_address)
        while True:
            try:
                response, new_server_addr = client_socket.recvfrom(2048)
                ack_opcode, ack_seq, _ = struct.unpack('!BIH', response[:7])
                if ack_opcode == 3 and ack_seq == 0:
                    server_address = new_server_addr
                    ack_received = True
                    print(f"[Handshake] Conectado al Worker en puerto: {server_address[1]}")
                    break
                else:
                    continue
            except socket.timeout:
                attempts += 1
                break

    if not ack_received:
        print(f"[Handshake] No se pudo conectar al Worker.")
        sys.exit(1)

    client_socket.setblocking(False)

    base = 1
    next_seq_num = 1
    paquetes_en_vuelo = {}
    archivo_terminado = False
    timeout_limit = 0.5

    cwnd = 2.0
    max_cwnd = 20.0
    paquetes_exitosos = 0

    print("\n[Transferencia] Iniciando Selective Repeat con AIMD...")
    with open(file_name, 'rb') as file:
        while not archivo_terminado or len(paquetes_en_vuelo) > 0:
            listos, _, _ = select.select([client_socket], [], [], 0.01)

            if listos:
                ack_pack, _ = client_socket.recvfrom(1024)
                if len(ack_pack) >= 7:
                    ack_opcode, ack_seq, _ = struct.unpack('!BIH', ack_pack[:7])

                    if ack_opcode == 3 and ack_seq in paquetes_en_vuelo and not paquetes_en_vuelo[ack_seq]['ack']:
                        paquetes_en_vuelo[ack_seq]['ack'] = True

                        paquetes_exitosos += 1
                        if paquetes_exitosos >= int(cwnd):
                            if cwnd < max_cwnd:
                                cwnd += 1.0
                                print(f"[AIMD] Ventana aumentada a {int(cwnd)}")
                            paquetes_exitosos = 0

                        while base in paquetes_en_vuelo and paquetes_en_vuelo[base]['ack']:
                            del paquetes_en_vuelo[base]
                            base += 1

            while next_seq_num < base + int(cwnd) and not archivo_terminado:
                block = file.read(1024)
                if not block:
                    archivo_terminado = True
                    break

                data_header = struct.pack('!BIH', 2, next_seq_num, len(block))
                packet = data_header + block

                paquetes_en_vuelo[next_seq_num] = {
                    'datos': packet,
                    'tiempo': time.time(),
                    'ack': False
                }

                client_socket.sendto(packet, server_address)
                next_seq_num += 1

            tiempo_actual = time.time()
            hubo_timeout = False

            for seq, info in paquetes_en_vuelo.items():
                if not info['ack'] and (tiempo_actual - info['tiempo'] > timeout_limit):
                    print(f"[SR] Timeout del paquete {seq}. Reenviando...")
                    client_socket.sendto(info['datos'], server_address)
                    info['tiempo'] = tiempo_actual
                    hubo_timeout = True

            if hubo_timeout:
                cwnd = max(cwnd / 2.0, 1.0)
                paquetes_exitosos = 0
                print(f"[AIMD] ¡Congestión detectada! Ventana reducida a {int(cwnd)}")

    client_socket.setblocking(True)
    client_socket.settimeout(0.2)

    final_header = struct.pack('!BIH', 7, next_seq_num, 0)
    ack_received = False
    attempts = 0

    print("\n[Cierre] Iniciando desconexión segura...")
    while not ack_received and attempts < max_attempts:
        client_socket.sendto(final_header, server_address)
        while True:
            try:
                ack_pack, _ = client_socket.recvfrom(1024)
                ack_opcode, ack_seq, _ = struct.unpack('!BIH', ack_pack[:7])
                if ack_opcode == 3 and ack_seq == next_seq_num:
                    ack_received = True
                    break
                else:
                    continue
            except socket.timeout:
                attempts += 1
                break

    print("¡Archivo transferido con éxito usando Selective Repeat!")
    client_socket.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cliente UDP Selective Repeat')
    parser.add_argument('--host', type=str, required=True, help='IP')
    parser.add_argument('--port', type=int, required=True, help='Puerto')
    parser.add_argument('--file', type=str, default='./documentos/test.txt', help='Archivo')
    args = parser.parse_args()
    start_upload(args.host, args.port, args.file)