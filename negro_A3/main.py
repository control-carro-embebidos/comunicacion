# ⚫ negro_A3.py — versión robusta sin reinicio forzado
from black_config_A3 import MI_ID, VECINOS
import network, socket, time, json, machine

PUERTO_UDP = 5005
sensor_temp = machine.ADC(4)

sta = network.WLAN(network.STA_IF)
sta.active(True)

def conectar_a_vecino():
    for ssid, pwd in VECINOS:
        print(f"[{MI_ID}] Intentando conectar a {ssid}...")
        sta.connect(ssid, pwd)
        for _ in range(10):  # Espera 10 segundos máximo
            if sta.isconnected():
                print(f"[{MI_ID}] Conectado a {ssid} con IP {sta.ifconfig()[0]}")
                return True
            time.sleep(1)
        print(f"[{MI_ID}] Falló conexión a {ssid}")
        sta.disconnect()
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

def enviar_mensaje(msg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(json.dumps(msg).encode(), ("192.168.4.1", PUERTO_UDP))
        s.close()
        print(f"[{MI_ID}] Mensaje enviado: {msg}")
    except:
        print(f"[{MI_ID}] Error al enviar mensaje")

# Reintenta hasta conectar con algún vecino
while not sta.isconnected():
    conectado = conectar_a_vecino()
    if not conectado:
        print(f"[{MI_ID}] Sin conexión. Esperando 10s antes de reintentar...")
        time.sleep(10)

# Bucle principal
while True:
    if not sta.isconnected():
        print(f"[{MI_ID}] Desconectado. Reintentando conexión...")
        conectar_a_vecino()
    else:
        msg = obtener_datos()
        enviar_mensaje(msg)
    time.sleep(4)
