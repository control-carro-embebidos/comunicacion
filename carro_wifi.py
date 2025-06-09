#*carro_wifi*
import machine
import time
import network
import socket
import json

# UART para comunicación con carro_ap
uart = machine.UART(0, baudrate=9600, tx=machine.Pin(0), rx=machine.Pin(1))

# Configuración WiFi
SSID = "CentralAP"
PASSWORD = "12345678"
HOST = "192.168.4.1"
PORT = 1234
LOCAL_PORT = 5555  # Puerto local forzado
MY_IP = "192.168.4.123"

wlan = network.WLAN(network.STA_IF)
wlan.ifconfig((MY_IP, '255.255.255.0', '192.168.4.1', '8.8.8.8'))

# Sensor de temperatura interna
def read_internal_temp():
    sensor_temp = machine.ADC(4)
    conversion_factor = 3.3 / 65535
    reading = sensor_temp.read_u16() * conversion_factor
    temperature = 27 - (reading - 0.706) / 0.001721
    return round(temperature, 2)

# Conexión WiFi
def connect_wifi():
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a WiFi...")
        wlan.ifconfig((MY_IP, '255.255.255.0', '192.168.4.1', '8.8.8.8'))
        wlan.connect(SSID, PASSWORD)
        timeout = 10
        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print("❌ Timeout conectando WiFi")
                break
            time.sleep(1)
    if wlan.isconnected():
        print("✅ WiFi conectado:", wlan.ifconfig())
    else:
        print("❌ No conectado a WiFi")

def ensure_wifi():
    if not wlan.isconnected():
        print("WiFi desconectado, intentando reconectar...")
        connect_wifi()

# Conectar al inicio
connect_wifi()

# Socket global para recibir y enviar
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', LOCAL_PORT))
s.setblocking(False)

# Enviar JSON al servidor central
def send_json(data):
    try:
        ensure_wifi()
        if not wlan.isconnected():
            print("No conectado a WiFi, no se envía")
            return

        json_str = json.dumps(data)
        s.sendto(json_str.encode(), (HOST, PORT))

        # Esperar respuesta opcional
        s.settimeout(2)
#         try:
#             resp, _ = s.recvfrom(1024)
#             print("📩 Respuesta del servidor:", resp.decode())
#         except Exception:
#             print("⚠️ No se recibió respuesta del servidor UDP")
    except Exception as e:
        print("❌ Error al enviar al servidor:", e)

# 💡 FUNCIONALIDAD QUE PIDES: Recibir datos del central y reenviar si no es para este nodo
def RecibirDelCentral():
    try:
        data, addr = s.recvfrom(4096)  # Amplié el buffer por si el mensaje es grande
        msg = data.decode('utf-8')  # Aseguramos que decodifique bien
        print("📥 UDP recibido:", msg)
        try:
            json_data = json.loads(msg)
            ip_destino = json_data.get("ip_destino", "")

            if ip_destino == MY_IP:
                print("📌 Mensaje dirigido a mí. Puedes procesarlo aquí.")
                # Aquí añades lógica para manejar el mensaje localmente
            else:
                print("➡️ Reenviando a carro_ap vía UART:", json_data)
                uart.write(json.dumps(json_data) + "\n")
        except json.JSONDecodeError as e:
            print("❌ Error al decodificar JSON:", e)
    except OSError:
        # No hay datos recibidos, puedes ignorar o loggear si quieres
        pass

# Variables de control
buffer = b""
last_send = 0
send_interval = 5  # segundos

# 🔁 Bucle principal
while True:
    RecibirDelCentral()

    # Leer UART y enviar a central
    if uart.any():
        buffer += uart.read()
        if b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            try:
                data_uart = json.loads(line.decode())
                print("📤 UART recibido:", data_uart)
                send_json(data_uart)
                print("➡️ Reenviando vía UDP:", data_uart)
            except Exception as e:
                print("❌ Error en JSON UART:", e)

    # Enviar temperatura propia periódicamente
    now = time.time()
    if now - last_send > send_interval:
        temp_wifi = read_internal_temp()
        data_prop = {"temp_carro_wifi": temp_wifi}
        print("🌡️ Enviando temperatura...")
        send_json(data_prop)
        last_send = now

    time.sleep(0.1)
