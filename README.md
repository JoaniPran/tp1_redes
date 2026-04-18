## Guía de Depuración

### Cómo monitorear el tráfico con Wireshark

Para que Wireshark pueda interpretar los paquetes de nuestro protocolo (Opcode, Secuencia, etc.) en lugar de mostrarlos como datos genéricos, se debe lanzar con el script de Lua adjunto:

```bash
wireshark -X lua_script:mi_protocolo.lua &
```
Pasos para la captura:

1. Abrir Wireshark con el comando anterior.
2. Seleccionar la interfaz Loopback: lo (ya que el tráfico es local 127.0.0.1).
3. Aplicar el filtro de visualización: fiuba_rdt (o el puerto: udp.port == 8080).

### Especificaciones Técnicas del Protocolo
**Estructura de la Cabecera (7 bytes)**

Utilizamos el formato de red Big-Endian (!) para evitar problemas de arquitectura (Endianness).

| Campo | Formato | Tamaño | Descripción |
| :--- | :--- | :--- | :--- |
| **Opcode** | `B` (unsigned char) | 1 byte | 0: Upload, 2: Datos, 3: ACK, 7: FIN |
| **Secuencia** | `I` (unsigned int) | 4 bytes | Número de secuencia del paquete |
| **Tamaño** | `H` (unsigned short) | 2 bytes | Longitud del payload (datos) |