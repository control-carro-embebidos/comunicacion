#**Carro_ap**
import machine
import network
import socket
import json
import time

# UART
uart = machine.UART(0, baudrate=9600, tx=machine.Pin(0), rx=machine.Pin(1))

# Temperatura interna (ADC4)
adc = machine.ADC(4)
def read_temp():
    voltage = adc.read_u16() * 3.3 / 65535
    return round(27 - (voltage - 0.706) / 0.001721, 2)

# Crear Access Point
SSID = "carro_ap"
PASSWORD = "12345678"
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=SSID, password=PASSWORD)

while not ap.active():
    pass
my_ip = ap.ifconfig()[0]
print("✅ AP activo:", ap.ifconfig())

# Socket UDP
UDP_PORT = 1234
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.setblocking(False)
udp_sock.bind((my_ip, UDP_PORT))

# Reenvío si no es para mí
FORWARD_IP = "192.168.4.17"
FORWARD_PORT = 5555
my_ipint = "192.168.4.123"

# Temporizador
last_send = 0
send_interval = 5  # segundos
uart_buffer = b""

while True:
    now = time.time()

    # Enviar temperatura periódicamente por UART
    if now - last_send >= send_interval:
        temp = read_temp()
        data = {"temp_carro_ap": temp}
        uart.write(json.dumps(data) + "\n")
        print("📤 UART (temp):", data)
        last_send = now

    # Escuchar por UDP
    try:
        data, addr = udp_sock.recvfrom(1024)
        msg = data.decode()
        print("📥 UDP de", addr, ":", msg)
        try:
            json_data = json.loads(msg)
            uart.write(json.dumps(json_data) + "\n")
            print("➡️ Reenviado por UART:", json_data)
        except Exception as e:
            print("❌ JSON inválido:", e)
            json_data = {"error": "JSON inválido"}

        response = {"status": "ok", "received": json_data}
        udp_sock.sendto(json.dumps(response).encode(), addr)

    except OSError:
        pass

    # Leer UART y reenviar si no es para mí
    if uart.any():
        uart_buffer += uart.read()
        if b"\n" in uart_buffer:
            line, uart_buffer = uart_buffer.split(b"\n", 1)
            try:
                received = json.loads(line.decode())
                ip_destino = received.get("ip_destino", "")
                
                if ip_destino == my_ipint:
                    print("📲 UART recibido (para mí):", received)
                    
                    # Aquí accedemos a los pasos del Carro_1
                    carro_1 = received.get("Carro_1", {})
                    for paso, datos in carro_1.items():
                        movimiento = datos.get("Movimiento", {})
                        brazo = datos.get("Brazo", {})
                        print(f"{paso}: Movimiento = {movimiento}, Brazo = {brazo}")

                else:
                    udp_sock.sendto(json.dumps(received).encode(), (FORWARD_IP, FORWARD_PORT))
                    print(f"🔁 UART redirigido a {FORWARD_IP}:{FORWARD_PORT}:", received)
            except Exception as e:
                print("⚠️ Error al decodificar UART:", e)

    time.sleep(0.1)
