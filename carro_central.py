import network
import socket
import json
import time
import select

# ——————————————————————————————————————————————————————————
# 1) Iniciar Access Point
# ——————————————————————————————————————————————————————————
def start_access_point(ssid: str, password: str):
    """
    Activa el Pico W en modo Access Point con SSID/PASSWORD.
    Devuelve (ap_obj, ip), donde ap_obj es el objeto WLAN y ip es la IP asignada.
    """
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=ssid, password=password)

    # Esperar hasta que el AP quede activo
    while not ap.active():
        time.sleep(0.2)

    ip, subnet, gateway, dns = ap.ifconfig()
    print("✅ AP activo:")
    print(f"    • SSID   : {ssid}")
    print(f"    • IP     : {ip}")
    print(f"    • Subnet : {subnet}")
    print(f"    • Gateway: {gateway}")
    print(f"    • DNS    : {dns}")
    return ap, ip

# ——————————————————————————————————————————————————————————
# 2) Configurar socket UDP
# ——————————————————————————————————————————————————————————
def setup_udp_socket(bind_ip: str, bind_port: int):
    """
    Crea un socket UDP no bloqueante en (bind_ip, bind_port).
    Devuelve el socket listo para usar.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((bind_ip, bind_port))
    s.setblocking(False)
    print(f"✅ Socket UDP enlazado en {bind_ip}:{bind_port}")
    return s

# ——————————————————————————————————————————————————————————
# 3) Chequear y reactivar el Access Point si se cae
# ——————————————————————————————————————————————————————————
def check_wifi(ap):
    """
    Si el Access Point (ap) no está activo, lo reactiva.
    """
    if not ap.active():
        print("❌ AP WiFi caído, reactivando...")
        ap.active(True)

# ——————————————————————————————————————————————————————————
# 4) Leer datos entrantes y responder
# ——————————————————————————————————————————————————————————
def handle_incoming(sock):
    """
    Revisa si hay datos entrantes en sock (UDP no bloqueante).
    Si llegan, los lee, parsea JSON, imprime en consola y responde con
    {"status":"ok","received":<json>}. Retorna True si leyó algo, o False si no había nada.
    """
    rlist, _, _ = select.select([sock], [], [], 0)
    if not rlist:
        return False  # No llegaron datos
    try:
        data, addr = sock.recvfrom(1024)
        if not data:
            return False
        mensaje = data.decode()
        print(f"📥 Recibido de {addr}: {mensaje}")

        try:
            json_data = json.loads(mensaje)
            print("    ✅ JSON parseado:", json_data)
        except ValueError as e:
            print("    ❌ Error al parsear JSON:", e)
            json_data = {"error": "JSON inválido"}

        # Responder al cliente
        respuesta = {"status": "ok", "received": json_data}
        sock.sendto(json.dumps(respuesta).encode(), addr)
        print(f"    📤 Respuesta enviada a {addr}: {respuesta}")
        return True
    except Exception as e:
        print("    🚫 Error en handle_incoming:", e)
        return False

# ——————————————————————————————————————————————————————————
# 5) Enviar mensaje personalizado a cualquier IP/puerto
# ——————————————————————————————————————————————————————————
def send_custom_message(sock, dest_ip: str, dest_port: int, payload: dict):
    """
    Envía payload (un dict) en JSON vía UDP a (dest_ip, dest_port).
    """
    try:
        msg_bytes = json.dumps(payload).encode()
        sock.sendto(msg_bytes, (dest_ip, dest_port))
        print(f"📤 Mensaje personalizado enviado a ({dest_ip}, {dest_port}): {payload}")
    except Exception as e:
        print(f"❌ Error enviando mensaje personalizado: {e}")

# ——————————————————————————————————————————————————————————
# 6) Función principal
# ——————————————————————————————————————————————————————————
def main():
    SSID = "CentralAP"
    PASSWORD = "12345678"
    UDP_PORT = 1234

    # 6.1) Arrancar Access Point
    ap, bind_ip = start_access_point(SSID, PASSWORD)

    # 6.2) Crear socket UDP
    udp_sock = setup_udp_socket(bind_ip, UDP_PORT)

    last_wifi_check = time.time()
    wifi_check_interval = 10       # Chequear AP cada 10 s
    last_temp_sent = 0
    send_temp_interval = 15        # Enviar temp cada 15 s

    print("📡 Servidor UDP en bucle principal. Ctrl+C para detener.")
    try:
        while True:
            # 6.3) Leer datos entrantes (handle_incoming)
            handle_incoming(udp_sock)

            # 6.4) Enviar temperatura cada cierto intervalo
            now = time.time()
            if now - last_temp_sent > send_temp_interval:
                carro_ip = "192.168.4.17"
                carro_port = 1234
                mensaje_salida = {
                    "comando": "actualizar_temp",
                    "temp": 26.9
                }
                send_custom_message(udp_sock, carro_ip, carro_port, mensaje_salida)
                last_temp_sent = now

            # 6.5) Chequear estado del AP periódicamente
            if now - last_wifi_check > wifi_check_interval:
                check_wifi(ap)
                last_wifi_check = now

            # Evitar bucle apretado
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n🛑 Bucle detenido por teclado.")
    finally:
        udp_sock.close()
        print("🔌 Socket UDP cerrado.")
        if ap.active():
            ap.active(False)
            print("🔌 Access Point desactivado.")

# ——————————————————————————————————————————————————————————
# 7) Punto de entrada
# ——————————————————————————————————————————————————————————
if __name__ == "__main__":
    main()

