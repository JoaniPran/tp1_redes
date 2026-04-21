import socket
import struct
import sys
import time
import select
import argparse
import os
from constants import (
    OPCODE_HANDSHAKE_INIT, OPCODE_DATA, OPCODE_ACK, OPCODE_EOF,
    HEADER_SIZE, PACKET_PAYLOAD_SIZE, SOCKET_RECV_BUFFER, ACK_BUFFER_SIZE,
    HANDSHAKE_TIMEOUT, SR_RETRANSMIT_TIMEOUT, SELECT_TIMEOUT,
    MAX_HANDSHAKE_ATTEMPTS, CWND_INITIAL, CWND_MAX, CWND_INCREMENT, CWND_BACKOFF, CWND_MIN,
    INITIAL_SEQ, INITIAL_ACK_SEQ
)

def start_upload(server_ip, server_port, file_name):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (server_ip, server_port)

    nombre_limpio = os.path.basename(file_name)

    header = struct.pack('!BIH', OPCODE_HANDSHAKE_INIT, INITIAL_ACK_SEQ, len(file_name))
    ack_received = False
    attempts = 0
    client_socket.settimeout(HANDSHAKE_TIMEOUT)

    while not ack_received and attempts < MAX_HANDSHAKE_ATTEMPTS:
        client_socket.sendto(header + nombre_limpio.encode('utf-8'), server_address)
        while True:
            try:
                response, new_server_addr = client_socket.recvfrom(SOCKET_RECV_BUFFER)
                ack_opcode, ack_seq, _ = struct.unpack('!BIH', response[:HEADER_SIZE])
                if ack_opcode == OPCODE_ACK and ack_seq == INITIAL_ACK_SEQ:
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

    base = INITIAL_SEQ
    next_seq_num = INITIAL_SEQ
    paquetes_en_vuelo = {}
    archivo_terminado = False

    cwnd = CWND_INITIAL
    paquetes_exitosos = 0

    print("\n[Transferencia] Iniciando Selective Repeat con AIMD...")
    with open(file_name, 'rb') as file:
        while not archivo_terminado or len(paquetes_en_vuelo) > 0:
            listos, _, _ = select.select([client_socket], [], [], SELECT_TIMEOUT)

            if listos:
                ack_pack, _ = client_socket.recvfrom(ACK_BUFFER_SIZE)
                if len(ack_pack) >= HEADER_SIZE:
                    ack_opcode, ack_seq, _ = struct.unpack('!BIH', ack_pack[:HEADER_SIZE])

                    if ack_opcode == OPCODE_ACK and ack_seq in paquetes_en_vuelo and not paquetes_en_vuelo[ack_seq]['ack']:
                        paquetes_en_vuelo[ack_seq]['ack'] = True

                        paquetes_exitosos += 1
                        if paquetes_exitosos >= int(cwnd):
                            if cwnd < CWND_MAX:
                                cwnd += CWND_INCREMENT
                                print(f"[AIMD] Ventana aumentada a {int(cwnd)}")
                            paquetes_exitosos = 0

                        while base in paquetes_en_vuelo and paquetes_en_vuelo[base]['ack']:
                            del paquetes_en_vuelo[base]
                            base += 1

            while next_seq_num < base + int(cwnd) and not archivo_terminado:
                block = file.read(PACKET_PAYLOAD_SIZE)
                if not block:
                    archivo_terminado = True
                    break

                # VERIFICAR TAMAÑO FIJO
                # en teoria solo el último paquete puede ser de menos de PACKET_PAYLOAD_SIZE bytes, si no es así hay un error
                is_last_dangling_packet = len(block) < PACKET_PAYLOAD_SIZE
                if is_last_dangling_packet:
                    archivo_terminado = True
                elif len(block) != PACKET_PAYLOAD_SIZE:
                    # Esto nunca debería ocurrir si read() funciona correctamente
                    print(f"[ERROR] Paquete {next_seq_num} tiene tamaño inválido: {len(block)}")
                    break

                data_header = struct.pack('!BIH', OPCODE_DATA, next_seq_num, len(block))
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
                if not info['ack'] and (tiempo_actual - info['tiempo'] > SR_RETRANSMIT_TIMEOUT):
                    print(f"[SR] Timeout del paquete {seq}. Reenviando...")
                    client_socket.sendto(info['datos'], server_address)
                    info['tiempo'] = tiempo_actual
                    hubo_timeout = True

            if hubo_timeout:
                cwnd = max(cwnd * CWND_BACKOFF, CWND_MIN)
                paquetes_exitosos = 0
                print(f"[AIMD] ¡Congestión detectada! Ventana reducida a {int(cwnd)}")

    client_socket.setblocking(True)
    client_socket.settimeout(HANDSHAKE_TIMEOUT)

    final_header = struct.pack('!BIH', OPCODE_EOF, next_seq_num, 0)
    ack_received = False
    attempts = 0

    print("\n[Cierre] Iniciando desconexión segura...")
    while not ack_received and attempts < MAX_HANDSHAKE_ATTEMPTS:
        client_socket.sendto(final_header, server_address)
        while True:
            try:
                ack_pack, _ = client_socket.recvfrom(ACK_BUFFER_SIZE)
                ack_opcode, ack_seq, _ = struct.unpack('!BIH', ack_pack[:HEADER_SIZE])
                if ack_opcode == OPCODE_ACK and ack_seq == next_seq_num:
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