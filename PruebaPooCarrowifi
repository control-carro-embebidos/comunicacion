from claseWifi import CarroWiFi

# Crear una instancia de la clase
carro = CarroWiFi(
    ssid="CentralAP",
    password="12345678",
    host="192.168.4.1",
    port=1234,
    local_port=5555,
    my_ip="192.168.4.123",
    uart_tx=0,
    uart_rx=1
)

while True:
    msg = carro.recibir_del_central()
    if msg:
        print("📥 UDP recibido:", msg)
        carro.send_json(msg)
