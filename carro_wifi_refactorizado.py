import machine
import time
import network
import socket
import json

# UART
uart = machine.UART(0, baudrate=9600, tx=machine.Pin(0), rx=machine.Pin(1))

# Config WiFi
SSID = "CentralAP"
PASSWORD = "12345678"
HOST = "192.168.4.1"
PORT = 1234
LOCAL_PORT = 5555
MY_IP = "192.168.4.123"

# Config WiFi STA
wlan = network.WLAN(network.STA_IF)
wlan.ifconfig((MY_IP, '255.255.255.0', '192.168.4.1', '8.8.8.8'))

# Socket UDP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('0.0.0.0', LOCAL_PORT))
s.setblocking(False)

# Buffer para UART
buffer = b""
last_send = 0
send_interval = 5  # segundos

# Lee temperatura interna del chip
def read_internal_temp():
    sensor_temp = machine.ADC(4)
    conversion_factor = 3.3 / 65535
    reading = sensor_temp.read_u16() * conversion_factor
    temperature = 27 - (reading - 0.706) / 0.001721
    return round(temperature, 2)

# Conecta al WiFi
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

# Verifica si sigue conectado
def ensure_wifi():
    if not wlan.isconnected():
        print("WiFi desconectado, intentando reconectar...")
        connect_wifi()

# Envía JSON por UDP
def send_json(data):
    try:
        ensure_wifi()
        if not wlan.isconnected():
            print("No conectado a WiFi, no se envía")
            return
        json_str = json.dumps(data)
        s.sendto(json_str.encode(), (HOST, PORT))
    except Exception as e:
        print("❌ Error al enviar al servidor:", e)

# Recibe mensaje del central y reenvía por UART si es necesario
def recibir_del_central():
    global buffer
    try:
        data, addr = s.recvfrom(4096)
        msg = data.decode('utf-8')
        print("📥 UDP recibido:", msg)
        try:
            json_data = json.loads(msg)
            ip_destino = json_data.get("ip_destino", "")
            if ip_destino == MY_IP:
                print("📌 Mensaje dirigido a mí.")
            else:
                print("➡️ Reenviando a carro_ap vía UART:", json_data)
                uart.write(json.dumps(json_data) + "\n")
            return json_data  # <- retorna el mensaje procesado
        except json.JSONDecodeError as e:
            print("❌ Error al decodificar JSON:", e)
            return None
    except OSError:
        return None

# Verifica si hay datos por UART y los envía al central
def check_uart():
    global buffer
    if uart.any():
        buffer += uart.read()
        if b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            try:
                data_uart = json.loads(line.decode())
                print("📤 UART recibido:", data_uart)
                send_json(data_uart)
                return data_uart  # <- retorna el mensaje leído
            except Exception as e:
                print("❌ Error en JSON UART:", e)
                return None
    return None

# Lee la temperatura y la envía al servidor
def enviar_temp():
    temp_wifi = read_internal_temp()
    data_prop = {"temp_carro_wifi": temp_wifi}
    print("🌡️ Enviando temperatura...")
    send_json(data_prop)
    return data_prop  # <- retorna el JSON enviado
