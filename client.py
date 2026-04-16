import socket
import sys
import argparse

def client(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message_count = 0
    
    while True:
        message = input("Enter a message to send (or 'exit' to quit): ")
        
        if message.lower() == 'exit':
            print("Exiting client.")
            break
        
        sock.sendto(message.encode(), (host, port))
        print(f"Sent message to {host}:{port}")
        
        message_count += 1
        
        # Recibir respuesta del servidor
        data, server_addr = sock.recvfrom(1024)
        response = data.decode()
        print(f"Received response from server: {response} at {server_addr}")
        
        # Primer mensaje: actualizar puerto al paralelo
        if message_count == 1:
            port = int(response)
            print(f"Updated to parallel port: {port}")
        
        # Tercer mensaje: verificar si recibimos Cierre
        if message_count == 3:
            if response == "Cierre":
                print("Server sent 'Cierre'. Closing client.")
                break
    
    sock.close()




def main():
    parser = argparse.ArgumentParser(description='UDP Client')
    parser.add_argument('--host', type=str, required=True, help='Server host address')
    parser.add_argument('--port', type=int, required=True, help='Server port')
    
    args = parser.parse_args()
    
    client(args.host, args.port)


if __name__ == '__main__':
    main()