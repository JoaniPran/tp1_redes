from mininet.net import Mininet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
import os

def run_topology():
    # Obtener el directorio donde está topo.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Crear Mininet sin controlador - funciona como bridge L2
    net = Mininet(link=TCLink)

    print("*** Añadiendo hosts (Servidor y Cliente)")
    server = net.addHost('h1', ip='10.0.0.1/24')
    client1 = net.addHost('h2', ip='10.0.0.2/24')
    client2 = net.addHost('h3', ip='10.0.0.3/24')
    
    print("*** Añadiendo Switch")
    switch = net.addSwitch('s1', failMode='standalone')

    print("*** Creando enlaces con 5% de pérdida en cada pata")
    net.addLink(server, switch, loss=5)
    net.addLink(client1, switch, loss=5)
    net.addLink(client2, switch, loss=5)

    print("*** Iniciando la red Mininet")
    net.start()
    
    print(f"*** Working directory: {script_dir}")
    # Cambiar al directorio del script para ambos hosts
    server.cmd(f'cd {script_dir}')
    client1.cmd(f'cd {script_dir}')
    client2.cmd(f'cd {script_dir}')

    print("*** Entrando a la consola interactiva")
    CLI(net)

    print("*** Deteniendo la red")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_topology()