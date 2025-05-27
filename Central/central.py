# -----------------------------------------
# 🧠 central.py
# -----------------------------------------
import socket, json

PUERTO_UDP = 5005

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", PUERTO_UDP))
print("[CENTRAL] Esperando datos...")

while True:
    data, addr = s.recvfrom(1024)
    try:
        msg = json.loads(data.decode())
        print(f"[CENTRAL] Recibido de {msg['from']} desde IP {addr[0]}:{addr[1]}: {msg['payload']}")
    except:
        print("[CENTRAL] Error de parseo")
