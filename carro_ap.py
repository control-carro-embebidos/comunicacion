import machine
import network
import socket
import json
import time

# Configuración principal
def setup_uart(uart_id=0, baudrate=9600, tx_pin=0, rx_pin=1):
    uart = machine.UART(uart_id, baudrate=baudrate, tx=machine.Pin(tx_pin), rx=machine.Pin(rx_pin))
    return uart


def setup_ap(ssid, password):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ssid, password=password)
    # Espera hasta que el AP esté activo
    while not ap.active():
        time.sleep(0.1)

    print("✅ AP activo:", ap.ifconfig())
    return ap


def setup_udp(bind_ip, bind_port, nonblocking=True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if nonblocking:
        sock.setblocking(False)
    sock.bind((bind_ip, bind_port))
    return sock


def read_temp(adc_pin=4):
    adc = machine.ADC(adc_pin)
    voltage = adc.read_u16() * 3.3 / 65535
    return round(27 - (voltage - 0.706) / 0.001721, 2)


def send_temp_over_uart(uart, interval, last_time_holder):
    now = time.time()
    if now - last_time_holder[0] >= interval:
        temp = read_temp()
        payload = json.dumps({"temp_carro_ap": temp}) + "\n"
        uart.write(payload)
        print("📤 UART (temp):", {"temp_carro_ap": temp})
        last_time_holder[0] = now


def handle_udp(uart, udp_sock, forward_ip, forward_port):
    try:
        data, addr = udp_sock.recvfrom(1024)
    except OSError:
        return

    msg = data.decode()
    print("📥 UDP de", addr, ":", msg)
    try:
        json_data = json.loads(msg)
        uart.write(json.dumps(json_data) + "\n")
        print("➡️ Reenviado por UART:", json_data)
    except Exception as e:
        print("❌ JSON inválido:", e)
        json_data = {"error": "JSON inválido"}

    # Responder a quien envió el UDP
    response = {"status": "ok", "received": json_data}
    udp_sock.sendto(json.dumps(response).encode(), addr)


def handle_uart(uart, udp_sock, my_ip, forward_ip, forward_port):
    buffer = getattr(handle_uart, 'buffer', b"")
    buffer += uart.read() if uart.any() else b""

    if b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        try:
            received = json.loads(line.decode())
            dest_ip = received.get("ip_destino", "")

            if dest_ip == my_ip:
                print("📲 UART recibido (para mí):", received)
                carro1 = received.get("Carro_1", {})
                for step, data in carro1.items():
                    mov = data.get("Movimiento", {})
                    brazo = data.get("Brazo", {})
                    print(f"{step}: Movimiento = {mov}, Brazo = {brazo}")
            else:
                udp_sock.sendto(json.dumps(received).encode(), (forward_ip, forward_port))
                print(f"🔁 UART redirigido a {forward_ip}:{forward_port}:", received)
        except Exception as e:
            print("⚠️ Error al decodificar UART:", e)

    handle_uart.buffer = buffer


def main_loop(uart, udp_sock, my_ip, forward_ip, forward_port, interval=5):
    last_send = [0]
    while True:
        send_temp_over_uart(uart, interval, last_send)
        handle_udp(uart, udp_sock, forward_ip, forward_port)
        handle_uart(uart, udp_sock, my_ip, forward_ip, forward_port)
        time.sleep(0.1)


if __name__ == "__main__":
    SSID = "carro_ap"
    PASSWORD = "12345678"
    FORWARD_IP = "192.168.4.17"
    FORWARD_PORT = 5555

    # Inicialización
    uart = setup_uart()
    ap = setup_ap(SSID, PASSWORD)
    ip = ap.ifconfig()[0]
    udp_sock = setup_udp(ip, 1234)

    # Ejecutar bucle principal
    main_loop(uart, udp_sock, ip, FORWARD_IP, FORWARD_PORT)
