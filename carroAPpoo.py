# clase_carro_ap.py
import machine
import network
import socket
import json
import time

class CarroAP:
    def __init__(self, ssid="carro_ap", password="12345678", udp_port=1234,
                 forward_ip="192.168.4.17", forward_port=5555, my_ipint="192.168.4.123"):
        
        self.ssid = ssid
        self.password = password
        self.udp_port = udp_port
        self.forward_ip = forward_ip
        self.forward_port = forward_port
        self.my_ipint = my_ipint

        # UART
        self.uart = machine.UART(0, baudrate=9600, tx=machine.Pin(0), rx=machine.Pin(1))
        self.uart_buffer = b""

        # ADC para temperatura
        self.adc = machine.ADC(4)

        # AP
        self.ap = network.WLAN(network.AP_IF)
        self.ap.active(True)
        self.ap.config(essid=self.ssid, password=self.password)

        while not self.ap.active():
            pass

        self.my_ip = self.ap.ifconfig()[0]
        print("✅ AP activo:", self.ap.ifconfig())

        # Socket UDP
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.setblocking(False)
        self.udp_sock.bind((self.my_ip, self.udp_port))

        # Temporizador
        self.last_send = 0
        self.send_interval = 5  # segundos

    def read_temp(self):
        voltage = self.adc.read_u16() * 3.3 / 65535
        return round(27 - (voltage - 0.706) / 0.001721, 2)

    def enviar_temp_uart(self):
        now = time.time()
        if now - self.last_send >= self.send_interval:
            temp = self.read_temp()
            data = {"temp_carro_ap": temp}
            self.uart.write(json.dumps(data) + "\n")
            print("📤 UART (temp):", data)
            self.last_send = now

    def escuchar_udp(self):
        try:
            data, addr = self.udp_sock.recvfrom(1024)
            msg = data.decode()
            print("📥 UDP de", addr, ":", msg)
            try:
                json_data = json.loads(msg)
                self.uart.write(json.dumps(json_data) + "\n")
                print("➡️ Reenviado por UART:", json_data)
            except Exception as e:
                print("❌ JSON inválido:", e)
                json_data = {"error": "JSON inválido"}

            response = {"status": "ok", "received": json_data}
            self.udp_sock.sendto(json.dumps(response).encode(), addr)

        except OSError:
            pass  # No hay datos

    def escuchar_uart(self):
        if self.uart.any():
            self.uart_buffer += self.uart.read()
            if b"\n" in self.uart_buffer:
                line, self.uart_buffer = self.uart_buffer.split(b"\n", 1)
                try:
                    received = json.loads(line.decode())
                    ip_destino = received.get("ip_destino", "")
                    
                    if ip_destino == self.my_ipint:
                        print("📲 UART recibido (para mí):", received)
                        carro_1 = received.get("Carro_1", {})
                        for paso, datos in carro_1.items():
                            mov = datos.get("Movimiento", {})
                            brazo = datos.get("Brazo", {})
                            print(f"{paso}: Movimiento = {mov}, Brazo = {brazo}")
                    else:
                        self.udp_sock.sendto(json.dumps(received).encode(),
                                             (self.forward_ip, self.forward_port))
                        print(f"🔁 UART redirigido a {self.forward_ip}:{self.forward_port}:", received)

                except Exception as e:
                    print("⚠️ Error al decodificar UART:", e)

    def ciclo_principal(self):
        while True:
            self.enviar_temp_uart()
            self.escuchar_udp()
            self.escuchar_uart()
            time.sleep(0.1)
