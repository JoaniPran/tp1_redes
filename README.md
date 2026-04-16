# tp1_redes
# tp1_redes


# Esquema
Cliente msg1 → Puerto principal → Worker thread
                                 → Envía puerto paralelo
Cliente msg2 → Puerto paralelo → Recibe ACK
Cliente msg3 → Puerto paralelo → Recibe Cierre → Cliente cierra

# Para correr server - cliente (uno o más)
```
python3 server.py --port 5000

python3 client.py --host localhost --port 5000

```