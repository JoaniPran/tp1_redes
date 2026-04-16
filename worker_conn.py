import socket

def handle_client(client_addr):
    print(f"Handling client at {client_addr}")

    #abrir un socket UDP paralelo para comunicarse con el cliente
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    sock.bind(('', 0))  # Bindeo a un puerto disponible
    local_port = sock.getsockname()[1]
    print(f"Worker socket bound to port {local_port}")

    #enviar el puerto al cliente para que sepa a dónde enviar los mensajes
    sock.sendto(str(local_port).encode(), client_addr)

    data, addr = sock.recvfrom(1024)  # Esperar a recibir un mensaje del cliente
    print(f"Received message from client {addr}: {data.decode()}")
    # Enviar ACK por cada mensaje recibido
    sock.sendto("ACK".encode(), addr)
    
    data, addr = sock.recvfrom(1024)
    print(f"Received message from client {addr}: {data.decode()}")
    print(f"Closing worker socket for client {client_addr}")
    sock.sendto("Cierre".encode(), client_addr)
    sock.close()