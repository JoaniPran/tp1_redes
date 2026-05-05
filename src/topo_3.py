from mininet.net import Mininet
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
import time
import os

def run_topology():
    # Obtener el directorio donde esta topo.py
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Crear Mininet SIN controlador (Correccion para Ubuntu)
    net = Mininet(controller=None, link=TCLink)

    print("*** Añadiendo hosts (Servidor y Cliente)")
    server = net.addHost('h1', ip='10.0.0.1/24')
    client1 = net.addHost('h2', ip='10.0.0.2/24')
    client2 = net.addHost('h3', ip='10.0.0.3/24')
    client3 = net.addHost('h4', ip='10.0.0.4/24')

    print("*** Añadiendo Switch")
    switch = net.addSwitch('s1', failMode='standalone')

    print("*** Creando enlaces con 5% de perdida en cada pata")
    net.addLink(server, switch, loss=5)
    net.addLink(client1, switch, loss=5)
    net.addLink(client2, switch, loss=5)
    net.addLink(client3, switch, loss=5)

    print("*** Iniciando la red Mininet")
    net.start()

    print(f"*** Working directory: {script_dir}")
    # Cambiar al directorio del script para los hosts
    server.cmd(f'cd {script_dir}')
    client1.cmd(f'cd {script_dir}')
    client2.cmd(f'cd {script_dir}')
    client3.cmd(f'cd {script_dir}')

    print("*** [Test] Levantando el servidor en h1...")
    server.cmd('python3 start-server -v > server.log 2>&1 &')

    time.sleep(1)

    print("*** [Test] Disparando los 3 clientes para DESCARGA simultanea...")
    # Asegurate de que los flags '-n' (remoto) y '-d' (destino local) coincidan con el parser de tu client_download.py
    client1.cmd('python3 download -H 10.0.0.1 -p 8080 -d ./descargas/down_1.bin -n test_15mb.bin -r sr -v > h2_download.log 2>&1 &')
    client2.cmd('python3 download -H 10.0.0.1 -p 8080 -d ./descargas/down_2.bin -n test_15mb_2.bin -r sr -v > h3_download.log 2>&1 &')
    client3.cmd('python3 download -H 10.0.0.1 -p 8080 -d ./descargas/down_3.bin -n test_15mb_3.bin -r sr -v > h4_download.log 2>&1 &')
    
    print("*** [Test] Descargas iniciadas. Revisa los .log para ver el progreso.")

    print("*** Entrando a la consola interactiva")
    CLI(net)

    print("*** Deteniendo la red")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_topology()