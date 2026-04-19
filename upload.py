import socket
import struct
import sys
import argparse
import os

def start_upload(server_ip, server_port, file_name):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (server_ip, server_port)
    print(f"Iniciando conexion con {server_address}...")

    nombre_limpio = os.path.basename(file_name)

    client_socket.settimeout(0.2)
    max_attempts = 25

    header = struct.pack('!BIH', 0, 0, len(nombre_limpio))
    ack_received = False
    attempts = 0

    while not ack_received and attempts < max_attempts:
        client_socket.sendto(header + nombre_limpio.encode('utf-8'), server_address)
        while True:
            try:
                response, new_server_addr = client_socket.recvfrom(1024)
                ack_opcode, ack_seq, _ = struct.unpack('!BIH', response[:7])

                if ack_opcode == 3 and ack_seq == 0:
                    server_address = new_server_addr
                    ack_received = True
                    print(f"Handshake OK. Empezando a subir al puerto privado: {server_address[1]}")
                    break
                else:
                    continue
            except socket.timeout:
                attempts += 1
                print(f"Timeout Handshake. Reintentando ({attempts}/{max_attempts})...")
                break

    if not ack_received:
        print("ERROR: No se pudo conectar (Handshake fallido). Abortando.")
        sys.exit(1)

    sequence_number = 1
    with open(file_name, 'rb') as file:
        while True:
            block = file.read(1024)
            if not block:
                break

            data_header = struct.pack('!BIH', 2, sequence_number, len(block))
            packet = data_header + block
            ack_received = False
            attempts = 0

            while not ack_received and attempts < max_attempts:
                client_socket.sendto(packet, server_address)
                while True:
                    try:
                        ack_pack, _ = client_socket.recvfrom(1024)
                        ack_opcode, ack_seq, _ = struct.unpack('!BIH', ack_pack[:7])

                        if ack_opcode == 3 and ack_seq == sequence_number:
                            print(f"Bloque {sequence_number} enviado y confirmado.")
                            ack_received = True
                            break
                        else:
                            continue
                    except socket.timeout:
                        attempts += 1
                        print(f"Timeout! Reenviando bloque {sequence_number} ({attempts}/{max_attempts})...")
                        break

            if not ack_received:
                print("ERROR: Conexion perdida en el medio del archivo. Abortando.")
                sys.exit(1)

            sequence_number += 1

    final_header = struct.pack('!BIH', 7, sequence_number, 0)
    ack_received = False
    attempts = 0

    print("Iniciando cierre de conexion...")
    while not ack_received and attempts < max_attempts:
        client_socket.sendto(final_header, server_address)
        while True:
            try:
                ack_pack, _ = client_socket.recvfrom(1024)
                ack_opcode, ack_seq, _ = struct.unpack('!BIH', ack_pack[:7])

                if ack_opcode == 3 and ack_seq == sequence_number:
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