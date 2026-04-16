import socket
import argparse
import threading

from worker_conn import handle_client

def server_start(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind((host, port))

    print(f"UDP server is listening on {host}:{port}")

    try:
        while True:
            data, client_addr = sock.recvfrom(1024)

            # Crear un nuevo hilo para manejar la conexión con el cliente
            worker = threading.Thread(target=handle_client, args=(client_addr,))

            # Hacer que el hilo sea un daemon para que 
            # se cierre automáticamente al finalizar el programa
            worker.daemon = True

            worker.start()

            print(f"Serv: Received message from {client_addr}: {data.decode()}")
    
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        sock.close()
        print("Server socket closed.")


def main():
    parser = argparse.ArgumentParser(description='UDP Server')
    parser.add_argument('--host', type=str, default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, required=True, help='Port to bind to')
    args = parser.parse_args()
    
    server_start(args.host, args.port)


if __name__ == '__main__':
    main()
