import socket
import struct
import sys
import argparse
import os
from constants import (
    OPCODE_HANDSHAKE_INIT, OPCODE_DATA, OPCODE_ACK, OPCODE_EOF,
    HEADER_SIZE, PACKET_PAYLOAD_SIZE, ACK_BUFFER_SIZE,
    HANDSHAKE_TIMEOUT, MAX_HANDSHAKE_ATTEMPTS, INITIAL_ACK_SEQ
)

def start_upload(server_ip, server_port, file_name):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (server_ip, server_port)
    print(f"Iniciando conexion con {server_address}...")

    nombre_limpio = os.path.basename(file_name)

    client_socket.settimeout(HANDSHAKE_TIMEOUT)

    header = struct.pack('!BIH', OPCODE_HANDSHAKE_INIT, INITIAL_ACK_SEQ, len(nombre_limpio))
    ack_received = False
    attempts = 0

    while not ack_received and attempts < MAX_HANDSHAKE_ATTEMPTS:
        client_socket.sendto(header + nombre_limpio.encode('utf-8'), server_address)
        while True:
            try:
                response, new_server_addr = client_socket.recvfrom(ACK_BUFFER_SIZE)
                ack_opcode, ack_seq, _ = struct.unpack('!BIH', response[:HEADER_SIZE])

                if ack_opcode == OPCODE_ACK and ack_seq == INITIAL_ACK_SEQ:
                    server_address = new_server_addr
                    ack_received = True
                    print(f"Handshake OK. Empezando a subir al puerto privado: {server_address[1]}")
                    break
                else:
                    continue
            except socket.timeout:
                attempts += 1
                print(f"Timeout Handshake. Reintentando ({attempts}/{MAX_HANDSHAKE_ATTEMPTS})...")
                break

    if not ack_received:
        print("ERROR: No se pudo conectar (Handshake fallido). Abortando.")
        sys.exit(1)

    sequence_number = 1
    with open(file_name, 'rb') as file:
        while True:
            block = file.read(PACKET_PAYLOAD_SIZE)
            if not block:
                break

            data_header = struct.pack('!BIH', OPCODE_DATA, sequence_number, len(block))
            packet = data_header + block
            ack_received = False
            attempts = 0

            while not ack_received and attempts < MAX_HANDSHAKE_ATTEMPTS:
                client_socket.sendto(packet, server_address)
                while True:
                    try:
                        ack_pack, _ = client_socket.recvfrom(ACK_BUFFER_SIZE)
                        ack_opcode, ack_seq, _ = struct.unpack('!BIH', ack_pack[:HEADER_SIZE])

                        if ack_opcode == OPCODE_ACK and ack_seq == sequence_number:
                            print(f"Bloque {sequence_number} enviado y confirmado.")
                            ack_received = True
                            break
                        else:
                            continue
                    except socket.timeout:
                        attempts += 1
                        print(f"Timeout! Reenviando bloque {sequence_number} ({attempts}/{MAX_HANDSHAKE_ATTEMPTS})...")
                        break

            if not ack_received:
                print("ERROR: Conexion perdida en el medio del archivo. Abortando.")
                sys.exit(1)

            sequence_number += 1

    final_header = struct.pack('!BIH', OPCODE_EOF, sequence_number, 0)
    ack_received = False
    attempts = 0

    print("Iniciando cierre de conexion...")
    while not ack_received and attempts < MAX_HANDSHAKE_ATTEMPTS:
        client_socket.sendto(final_header, server_address)
        while True:
            try:
                ack_pack, _ = client_socket.recvfrom(ACK_BUFFER_SIZE)
                ack_opcode, ack_seq, _ = struct.unpack('!BIH', ack_pack[:HEADER_SIZE])

                if ack_opcode == OPCODE_ACK and ack_seq == sequence_number:
                    ack_received = True
                    break
                else:
                    continue
            except socket.timeout:
                attempts += 1
                break

    print("\n¡Archivo transferido con exito!")
    client_socket.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cliente UDP RDT')
    parser.add_argument('--host', type=str, required=True, help='IP del Servidor')
    parser.add_argument('--port', type=int, required=True, help='Puerto del Servidor (Mesa de entradas)')
    parser.add_argument('--file', type=str, default='./documentos/test.txt', help='Archivo a subir')

    args = parser.parse_args()
    start_upload(args.host, args.port, args.file)