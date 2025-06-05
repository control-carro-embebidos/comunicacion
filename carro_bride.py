import network
import socket
import json
import time
import select
import machine

# ——————————————————————————————————————
# CONFIGURACIÓN
# ——————————————————————————————————————
SSID = "CentralAP"
PASSWORD = "12345678"
UDP_PORT = 1234
UART_BAUDRATE = 9600
UART_TX_PIN = 0
UART_RX_PIN = 1

# ——————————————————————————————————————
# 1) Iniciar Access Point
# ——————————————————————————————————————
def start_ap(ssid, password):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ssid, password=password)
    while not ap.active():
        time.sleep(0.2)
    print("✅ AP activo:", ap.ifconfig())
    return ap, ap.ifconfig()[0]

# ——————————————————————————————————————
# 2) Configurar socket UDP no bloqueante
# ——————————————————————————————————————
def setup_udp_socket(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.setblocking(False)
    print(f"📡 Socket UDP escuchando en {ip}:{port}")
    return s

# ——————————————————————————————————————
# 3) Configurar UART
# ——————————————————————————————————————
def setup_uart(tx_pin, rx_pin, baudrate):
    uart = machine.UART(0, baudrate=baudrate, tx=machine.Pin(tx_pin), rx=machine.Pin(rx_pin))
    print("🔌 UART lista")
    return uart

# ——————————————————————————————————————
# 4) Procesar mensajes UDP entrantes y reenviar por UART
# ——————————————————————————————————————
def handle_udp_input(sock, uart):
    try:
        data, addr = sock.recvfrom(1024)
        if data:
            msg = data.decode()
            print(f"📥 UDP recibido de {addr}: {msg}")
            try:
                json_msg = json.loads(msg)
                uart.write(json.dumps(json_msg) + "\n")
                print(f"🔁 Reenviado por UART: {json_msg}")
                return addr  # guardar dirección de último cliente
            except Exception as e:
                print("❌ Error al parsear JSON de UDP:", e)
    except Exception:
        pass
    return None

# ——————————————————————————————————————
# 5) Procesar mensajes UART entrantes y reenviar por UDP
# ——————————————————————————————————————
def handle_uart_input(uart, udp_sock, last_udp_addr, buffer):
    if uart.any():
        buffer += uart.read()
        if b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            try:
                json_data = json.loads(line.decode())
                print("📥 UART recibido:", json_data)
                if last_udp_addr:
                    udp_sock.sendto(json.dumps(json_data).encode(), last_udp_addr)
                    print(f"📤 Enviado a último UDP {last_udp_addr}: {json_data}")
                else:
                    print("⚠️ No hay cliente UDP reciente para responder.")
            except Exception as e:
                print("❌ Error parseando JSON UART:", e)
    return buffer

# ——————————————————————————————————————
# 6) Chequear que el AP siga activo
# ——————————————————————————————————————
def check_ap(ap):
    if not ap.active():
        print("❌ AP caído. Reactivando...")
        ap.active(True)

# ——————————————————————————————————————
# 7) Función principal
# ——————————————————————————————————————
def main():
    ap, ip = start_ap(SSID, PASSWORD)
    udp_sock = setup_udp_socket(ip, UDP_PORT)
    uart = setup_uart(UART_TX_PIN, UART_RX_PIN, UART_BAUDRATE)

    buffer_uart = b""
    last_wifi_check = time.time()
    last_udp_client = None

    try:
        while True:
            # 1. Procesar entrada UDP y reenviar por UART
            addr = handle_udp_input(udp_sock, uart)
            if addr:
                last_udp_client = addr

            # 2. Procesar entrada UART y reenviar por UDP
            buffer_uart = handle_uart_input(uart, udp_sock, last_udp_client, buffer_uart)

            # 3. Verificar estado del AP cada 10 segundos
            if time.time() - last_wifi_check > 10:
                check_ap(ap)
                last_wifi_check = time.time()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n🛑 Detenido por usuario.")
    finally:
        udp_sock.close()
        if ap.active():
            ap.active(False)
        print("🔌 Limpieza final completa.")

# ——————————————————————————————————————
# Ejecutar
# ——————————————————————————————————————
if __name__ == "__main__":
    main()

