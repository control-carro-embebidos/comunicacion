# 🔴 rojo_A2.py
from red_config_A2 import MI_ID
import network, socket, time, json, machine

PUERTO_UDP = 5005
sensor_temp = machine.ADC(4)
CENTRAL_IP = "192.168.4.17"  # IP del PC conectado al AP del nodo rojo

# Activar AP
AP = network.WLAN(network.AP_IF)
AP.config(essid=MI_ID, password="12345678")
AP.active(True)

# STA no se necesita porque ya no se conecta a otros
# Solo recibe y reenvía

def leer_temperatura():
    conversion_factor = 3.3 / 65535
    lectura = sensor_temp.read_u16() * conversion_factor
    temperatura_c = 27 - (lectura - 0.706) / 0.001721
    return round(temperatura_c, 2)

def obtener_datos():
    return {
        "from": MI_ID,
        "to": "central",
        "type": "sensor_data",
        "payload": {"temperatura": leer_temperatura()},
        "visited": [MI_ID]
    }

def retransmitir(msg):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(json.dumps(msg).encode(), (CENTRAL_IP, PUERTO_UDP))
    print(f"[{MI_ID}] Reenviado a CENTRAL ({CENTRAL_IP}): {msg}")
    s.close()

# Socket para escuchar
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", PUERTO_UDP))
s.setblocking(False)

contador_envio = 0
intervalo_envio = 15

print(f"[{MI_ID}] AP activo. Esperando mensajes...")

while True:
    try:
        data, addr = s.recvfrom(1024)
        msg = json.loads(data.decode())
        print(f"[{MI_ID}] Recibido de {msg['from']} -> {msg['payload']}")
        if MI_ID not in msg["visited"]:
            msg["visited"].append(MI_ID)
            retransmitir(msg)
    except:
        pass

    if contador_envio <= 0:
        msg = obtener_datos()
        retransmitir(msg)
        contador_envio = intervalo_envio
    else:
        contador_envio -= 1

    time.sleep(1)
