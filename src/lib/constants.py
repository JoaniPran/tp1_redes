"""
Constantes. Si usan algún numero arbitrario que pueda ser reutilizado en otro lado, dejenlo acá.
"""

# ============================================================================
# PROTOCOLOS Y OPCODES
# ============================================================================
# Códigos de operación del protocolo
OPCODE_HANDSHAKE_INIT = 0      # Cliente inicia: pide upload
OPCODE_DATA = 2                # Datos de archivo
OPCODE_ACK = 3                 # Confirmación de recepción
OPCODE_EOF = 7                 # Fin de archivo

# ============================================================================
# TAMAÑOS DE PAQUETE Y BUFFER
# ============================================================================
PACKET_PAYLOAD_SIZE = 1024      # Tamaño fijo de payload por paquete (bytes)
HEADER_SIZE = 7                 # Tamaño del header (opcode:1B + seq:4B + size:2B)
SOCKET_RECV_BUFFER = 2048       # Buffer de recepción en socket
ACK_BUFFER_SIZE = 1024          # Buffer mínimo para recibir ACKs
MAX_FILE_SIZE = 20 * 1024 * 1024  # Tamaño máximo de archivo permitido (20 MB)

# ============================================================================
# TIMEOUTS (segundos)
# ============================================================================
HANDSHAKE_TIMEOUT = 0.2         # Timeout para handshake inicial
WORKER_SOCKET_TIMEOUT = 10.0    # Timeout general del socket del worker
SR_RETRANSMIT_TIMEOUT = 0.5     # Timeout para retransmisión en Selective Repeat
SELECT_TIMEOUT = 0.01           # Timeout de select() para polling no bloqueante

# ============================================================================
# REINTENTOS
# ============================================================================
MAX_HANDSHAKE_ATTEMPTS = 25     # Intentos máximos en handshake
MAX_RETRANSMIT_ATTEMPTS = 25    # Intentos máximos de retransmisión

# ============================================================================
# CONTROL DE CONGESTIÓN (Additive Increase, Multiplicative Decrease)
# ============================================================================
CWND_INITIAL = 2.0              # Ventana de congestión inicial
CWND_MAX = 20.0                 # Ventana máxima
CWND_INCREMENT = 1.0            # Incremento
CWND_BACKOFF = 0.5              # Factor de reducción multiplicativa (divide por 2)
CWND_MIN = 1.0                  # Ventana mínima

# ============================================================================
# SECUENCIAS INICIALES
# ============================================================================
INITIAL_SEQ = 1                 # Primer número de secuencia
INITIAL_ACK_SEQ = 0             # Número de secuencia del ACK de handshake

# ============================================================================
# NOMBRE DE ARCHIVOS TEMPORALES
# ============================================================================
TEMP_FILE_PREFIX = ".tmp_"      # Prefijo para archivos temporales durante transferencia
