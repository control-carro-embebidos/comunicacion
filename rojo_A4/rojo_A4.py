# 🔴 rojo_A4.py
from red_config_A4 import MI_ID, VECINOS
import network, socket, time, json, machine

PUERTO_UDP = 5005
sensor_temp = machine.ADC(4)

# Activar AP (para que otros nodos como negro se conecten a este)
AP = network.WLAN(network.AP_IF)
AP.config(essid=MI_ID, password="12345678")
AP.active(True)

# STA para conectarse a vecinos (rojos o central)
STA = network.WLAN(network.STA_IF)
STA.active(True)

def conectar_a_vecino():
    for ssid, pwd in VECINOS:
        print(f"[{MI_ID}] Intentando conectar a {ssid}...")
        STA.connect(ssid, pwd)
        for _ in range(10):
            if STA.isconnected():
                print(f"[{MI_ID}] Conectado a {ssid} con IP {STA.ifconfig()[0]}")
                return True
            time.sleep(1)
        print(f"[{MI_ID}] Falló conexión a {ssid}")
    return False

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
    if not STA.isconnected():
        print(f"[{MI_ID}] STA no conectada. Intentando reconectar...")
        if not conectar_a_vecino():
            print(f"[{MI_ID}] No se pudo conectar a ningún vecino.")
            return

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(json.dumps(msg).encode(), ("192.168.4.1", PUERTO_UDP))  # IP por defecto del AP del vecino
        print(f"[{MI_ID}] Reenviado a vecino: {msg}")
        s.close()
    except Exception as e:
        print(f"[{MI_ID}] Error al retransmitir: {e}")

# Socket para escuchar como AP
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
