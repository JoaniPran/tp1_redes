import socket
import threading
import argparse
from worker_sr import handle_client
from constants import OPCODE_HANDSHAKE_INIT, HEADER_SIZE, SOCKET_RECV_BUFFER

def server_start(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"Servidor despachador escuchando en {host}:{port}")

    try:
        while True:
            data, client_addr = sock.recvfrom(SOCKET_RECV_BUFFER)

            if len(data) >= HEADER_SIZE:
                opcode = data[0]

                if opcode == OPCODE_HANDSHAKE_INIT:
                    print(f"\n[Despachador] Nuevo cliente: {client_addr}. Creando worker...")
                    worker = threading.Thread(target=handle_client, args=(data, client_addr))
                    worker.daemon = True
                    worker.start()
                else:
                    print(f"[Despachador] Ignorado. Opcode incorrecto para inicio: {opcode}")

    except KeyboardInterrupt:
        print("\nApagando servidor...")
    finally:
        sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Servidor UDP.')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='IP de escucha')
    parser.add_argument('--port', type=int, required=True, help='Puerto de escucha')

    args = parser.parse_args()
    server_start(args.host, args.port)