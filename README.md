# Requisitos del sistema
Para ejecutar esta aplicación es necesario:
- **Python3**
- **Mininet:** Para la simulación de la topología de red y perdida de paquetes
- **Wireshark (Opcional):** Para el analisis de tráfico y depuración

# Guía de uso
## Interfaz del Servidor
    > python3 src/start-server -h

    usage : src/start-server [ -h ] [ -v | -q ] [ -H ADDR ] [ -p PORT ] [ -s DIRPATH ]

    < command description >
    optional arguments :
        -h , --help -> show this help message and exit
        -v , --verbose -> increase output verbosity
        -q , --quiet -> decrease output verbosity
        -H , --host -> service IP address
        -p , --port -> service port
        -s , --storage -> storage dir path

## Interfaz del Cliente Upload

    > python3 src/upload -h

    usage : upload [ -h ] [ -v | -q ] [ -H ADDR ] [ -p PORT ] [ -s FILEPATH ] [ -n FILENAME ] [ -r protocol ]

    < command description >
    optional arguments :
        -h , --help -> show this help message and exit
        -v , --verbose increase output verbosity
        -q , --quiet -> decrease output verbosity
        -H , --host -> server IP address
        -p , --port -> server port
        -s , --src -> source file path
        -n , --name -> name under which the file is saved
        -r , --protocol error recovery protocol

## Interfaz del Cliente Download

    > python3 src/download -h
    
    usage : download [ -h ] [ -v | -q ] [ -H ADDR ] [ -p PORT ] [ -d FILEPATH ] [ -n FILENAME ] [ -r protocol ]
    
    < command description >
    optional arguments :
        -h , --help -> show this help message and exit
        -v , --verbose -> increase output verbosity
        -q , --quiet -> decrease output verbosity
        -H , --host -> server IP address
        -p , --port -> server port
        -d , --dst -> destination file path
        -n , --name -> name under which the file is saved
        -r , --protocol -> error recovery protocol. (sw = stop and wait)(sr = selective repeat)


## Configuración del Entorno de mininet
Se provee un script de topología personalizada (```topo.py```) que levanta 3 nodos (1 Servidor y 2 Clientes) conectados a un switch central, con una perdida de paquetes del 5% en cada enlace, lo que da como resultado un 10% de tasa total en el camino Cliente-Servidor

### 1. Iniciar topología.
```bash
sudo python3 topo.py
```
### 2. Una vez en el prompt interactivo de Mininet(```mininet>```), abrir las terminales de los hosts.
```bash
mininet> xterm h1 h2 h3
```
**nota:** En caso de querer abrir la terminal de 2 hosts, es posible, eliminando ```h3``` del comando anterior

## Ejecución
### 1. Iniciar el servidor.

```bash
python3 src/start-server -H <IP_BIND> -p <PUERTO> -s <DIRECTORIO_ALMACENAMIENTO> [-v | -q]
```
**Ejemplo de uso:**
```bash
python3 src/start-server -v
```

### 2. Iniciar clientes:

### - Upload
Transfiere un archivo desde el almacenamiento local del cliente hacia el servidor.

En la terminal de un cliente (ej. ```h2```), ejecutar:

    python3 src/upload -H <IP_SERVIDOR> -p <PUERTO> -s <RUTA_ARCHIVO_ORIGEN> -n <NOMBRE_DESTINO> -r <PROTOCOLO> [-v | -q]
    

**Ejemplo de uso (Selective repeat)**
```bash
python3 src/upload -H 10.0.0.1 -p 8080 -s ./documentos/test_15mb.bin -n test_15mb.bin -r sr -v
```

### - Download
Descarga un archivo existente en el servidor hacia el almacenamiento local del cliente. 

En la terminal de un cliente (ej. ```h3```), ejecutar:

    python3 src/download -H <IP_SERVIDOR> -p <PUERTO> -d <RUTA_ARCHIVO_DESTINO> -n <NOMBRE_ORIGEN> -r <PROTOCOLO> [-v | -q]

**Ejemplo de uso (Selective repeat)**

    python3 src/download -H 10.0.0.1 -p 8080 -d ./descargas/archivo_recibido.bin -n test_15mb.bin -r sw -v


# Guía de Depuración
## Cómo monitorear el tráfico con Wireshark

Para que Wireshark pueda interpretar los paquetes de nuestro protocolo (Opcode, Secuencia, etc.) en lugar de mostrarlos como datos genéricos, se debe lanzar con el script de Lua adjunto:

Hay 2 opciones.

**Opción 1:** Ejecutar el siguiente comando
```bash
wireshark -X lua_script:mi_protocolo.lua &
```

**Opción 2:**
 
1. Iniciar Wireshark normalmente
2. Ir a la pestaña Help -> About Wireshark
3. En la pestaña de ayuda ir a Folders -> Personal Lua Plugins
4. Copiar el archivo ```mi_protocolo.lua``` y pegarlo en el directorio de plugins


### Pasos para la captura:

1. Abrir Wireshark con el comando anterior.
2. Seleccionar la interfaz Loopback: lo (ya que el tráfico es local 127.0.0.1).
3. Aplicar el filtro de visualización: fiuba_rdt (o el puerto: udp.port == 8080).

### Especificaciones Técnicas del Protocolo
**Estructura de la Cabecera (7 bytes)**

Utilizamos el formato de red Big-Endian (!) para evitar problemas de arquitectura (Endianness).

| Campo | Formato | Tamaño | Descripción |
| :--- | :--- | :--- | :--- |
| **Opcode** | `B` (unsigned char) | 1 byte | 0: HANDSHAKE (Upload), 1: DOWNLOAD, 2: DATA, 3: ACK, 4: ERROR, 7: CLOSE (FIN) |
| **Secuencia** | `I` (unsigned int) | 4 bytes | Número de secuencia del paquete |
| **Tamaño** | `H` (unsigned short) | 2 bytes | Longitud del payload (datos) |

**Descripción de Opcodes:**
- **0 - HANDSHAKE (Upload):** Inicia una transferencia de archivo desde cliente a servidor
- **1 - DOWNLOAD:** Solicita la descarga de un archivo del servidor
- **2 - DATA:** Paquete de datos con contenido del archivo
- **3 - ACK:** Confirmación de recepción de datos
- **4 - ERROR:** Notificación de error en la transferencia
- **7 - CLOSE (FIN):** Cierra la conexión y finaliza la transferencia