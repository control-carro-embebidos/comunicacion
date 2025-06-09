#*central*
import network
import socket
import json
import time
import select

SSID = "CentralAP"
PASSWORD = "12345678"

# Configurar Access Point
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=SSID, password=PASSWORD)

json_data = {
    "mensaje": "Hola desde la central (mensaje de prueba)",
    "ip_destino": "192.168.4.60",
      "Carro_1":{
        "Paso_1":{
            "Movimiento":{"distancia_mm":100, "velocidad_mm_s":50, "radio_mm":"inf"},
            "Brazo":{"angulo0_grados":0, "angulo1_grados":0, "angulo2_grados":0}
            },
        "Paso_2":{
            "Movimiento":{"distancia_mm":0, "velocidad_mm_s":0, "radio_mm":0},
            "Brazo":{"angulo0_grados":0, "angulo1_grados":90, "angulo2_grados":0}
            },
        "Paso_3":{
            "Movimiento":{"distancia_mm":0, "velocidad_mm_s":0, "radio_mm":0},
            "Brazo":{"angulo0_grados":0, "angulo1_grados":0, "angulo2_grados":90}
            },
        "Paso_4":{
            "Movimiento":{"distancia_mm":0, "velocidad_mm_s":0, "radio_mm":0},
            "Brazo":{"angulo0_grados":0, "angulo1_grados":0, "angulo2_grados":-90}
            },
        "Paso_5":{
            "Movimiento":{"distancia_mm":0, "velocidad_mm_s":0, "radio_mm":0},
            "Brazo":{"angulo0_grados":0, "angulo1_grados":0, "angulo2_grados":90}
            },
        "Paso_6":{
            "Movimiento":{"distancia_mm":0, "velocidad_mm_s":0, "radio_mm":0},
            "Brazo":{"angulo0_grados":0, "angulo1_grados":0, "angulo2_grados":-90}
            },
        "Paso_7":{
            "Movimiento":{"distancia_mm":0, "velocidad_mm_s":0, "radio_mm":0},
            "Brazo":{"angulo0_grados":0, "angulo1_grados":-90, "angulo2_grados":0}
            },
        "Paso_8":{
            "Movimiento":{"distancia_mm":100, "velocidad_mm_s":50, "radio_mm":50},
            "Brazo":{"angulo0_grados":-90, "angulo1_grados":0, "angulo2_grados":0}
            }
        },
    "timestamp": time.time(),
    "status": "ok"
}

while not ap.active():
    time.sleep(1)

print("✅ AP activo:", ap.ifconfig())  # IP: 192.168.4.1

HOST = ap.ifconfig()[0]
PORT = 1234

# Crear socket UDP no bloqueante
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))
s.setblocking(False)  # No bloqueante

print(f"📡 Servidor UDP escuchando en {HOST}:{PORT}")

# ------------------------- FUNCIONES -------------------------

def check_wifi():
    if not ap.active():
        print("❌ AP WiFi caído, reactivando...")
        ap.active(True)

def recibir_mensaje():
    """
    Revisa si hay mensajes entrantes y devuelve la IP y el mensaje si hay.
    """
    rlist, _, _ = select.select([s], [], [], 1)
    if rlist:
        try:
            data, addr = s.recvfrom(1024)
            if data:
                message = data.decode()
                print(f"📥 Recibido de {addr}: {message}")
                try:
                    json_data = json.loads(message)
                    print("✅ JSON recibido:", json_data)
                except Exception as e:
                    print("❌ Error al parsear JSON:", e)
                    json_data = {"error": "JSON inválido"}

                return addr[0], addr[1], json_data  # IP, puerto, datos
        except Exception as e:
            print("🚫 Error recibiendo datos UDP:", e)
    return None, None, None

def enviar_json_a_dispositivo(ip_destino, puerto_destino, json_data):
    """
    Envía un JSON de prueba a un dispositivo conectado con IP y puerto conocidos.
    """


    try:
        mensaje = json.dumps(json_data)
        s.sendto(mensaje.encode(), (ip_destino, puerto_destino))
        print(f"📤 JSON enviado a {ip_destino}:{puerto_destino}")
    except Exception as e:
        print("❌ Error al enviar JSON:", e)

# ------------------------- LOOP PRINCIPAL -------------------------

last_wifi_check = 0
wifi_check_interval = 10  # segundos

# Dirección IP y puerto del cliente (ajusta esto)
ip_cliente_objetivo = "192.168.4.2"
puerto_cliente_objetivo = 5678

while True:
    # Detectar si llegó un mensaje entrante
    
    ip_remitente, puerto_remitente, datos = recibir_mensaje()
    # Enviar mensaje de prueba al cliente conocido
    enviar_json_a_dispositivo("192.168.4.17", 5525, json_data)
    enviar_json_a_dispositivo("192.168.4.123", 5555, json_data)
    # Chequeo periódico del AP
    now = time.time()
    if now - last_wifi_check > wifi_check_interval:
        check_wifi()
        last_wifi_check = now

    time.sleep(2)  # Evitar enviar mensajes en bucle rápidoa
