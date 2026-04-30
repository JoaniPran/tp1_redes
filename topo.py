from mininet.net import Mininet
from mininet.node import OVSController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel

def run_topology():
    # Es crucial pasar TCLink para poder simular pérdidas
    net = Mininet(controller=OVSController, link=TCLink)

    print("*** Añadiendo controlador")
    net.addController('c0')

    print("*** Añadiendo hosts (Servidor y Cliente) y Switch")
    server = net.addHost('h1', ip='10.0.0.1/24')
    client = net.addHost('h2', ip='10.0.0.2/24')
    switch = net.addSwitch('s1')

    print("*** Creando enlaces con 5% de pérdida en cada pata (~9.75% total)")
    # Si quieres el 10% de un solo lado, pon loss=10 en uno y loss=0 en el otro.
    net.addLink(server, switch, loss=5)
    net.addLink(client, switch, loss=5)

    print("*** Iniciando la red Mininet")
    net.start()

    print("*** Entrando a la consola interactiva")
    CLI(net)

    print("*** Deteniendo la red")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run_topology()