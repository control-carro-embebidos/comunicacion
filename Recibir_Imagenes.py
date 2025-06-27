import machine
import time
import urequests as requests
import sys
import ujson
from machine import Pin, I2C, PWM
from ov7670_wrapper import * # Assuming this is your custom camera wrapper
import gc
import network

# Global counter for image sequence
image_sequence_number = 0

def conectar_wifi_estatico(ssid, password, ip_estatica, mascara_subred, puerta_enlace, dns_primario, dns_secundario=None):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Conectando a la red Wi-Fi con IP estática...')
        wlan.ifconfig((ip_estatica, mascara_subred, puerta_enlace, dns_primario)) 
        
        wlan.connect(ssid, password)
        timeout = 20 
        while not wlan.isconnected() and timeout > 0:
            print('.', end='')
            time.sleep(1)
            timeout -= 1
            
    if wlan.isconnected():
        print('\nConectado a Wi-Fi.')
        print(f'IP: {wlan.ifconfig()[0]}')
        print(f'Máscara de subred: {wlan.ifconfig()[1]}')
        print(f'Puerta de enlace: {wlan.ifconfig()[2]}')
        print(f'DNS: {wlan.ifconfig()[3]}')
        return True
    else:
        print('\nError: no se pudo conectar a Wi-Fi')
        return False

# --- Network Data (ADJUST THESE VALUES TO YOUR NETWORK!) ---
SSID = "CentralAPT"
PASSWORD = "12345678"
IP_ESTATICA = "192.168.0.200"  # The IP you want your microcontroller to have
MASCARA_SUBRED = "255.255.255.0"
PUERTA_ENLACE = "192.168.0.254"    # Your router's IP or gateway
DNS_PRIMARIO = "8.8.8.8"      # A public DNS server (Google DNS)
DNS_SECUNDARIO = "8.8.4.4"    # Another public DNS server

# The IP of the server where you'll send images
FLASH_SERVER_URL = "http://192.168.0.100:8000" 

if not conectar_wifi_estatico(SSID, PASSWORD, IP_ESTATICA, MASCARA_SUBRED, PUERTA_ENLACE, DNS_PRIMARIO, DNS_SECUNDARIO):
    print("No conectado a Wi-Fi, abortando...")
    sys.exit()

# --- Rest of the code (significant changes here for sequence number) ---

UPLOAD_ENDPOINT = "/upload_raw_image_flash/"
TIMEOUT_SECONDS = 30
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
DEVICE_IP = IP_ESTATICA 

# Camera pins
mclk_pin_no = 22
pclk_pin_no = 21
data_pin_base = 2
vsync_pin_no = 17
href_pin_no = 26
reset_pin_no = 14
shutdown_pin_no = 15
sda_pin_no = 12
scl_pin_no = 13
led_pin = Pin(1, Pin.OUT)

# PWM for MCLK
print("Configuring MCLK for OV7670 on GP22...")
pwm = PWM(Pin(mclk_pin_no))
pwm.freq(30_000_000)
pwm.duty_u16(32768)

# Initialize I2C and camera
print("Initializing I2C and OV7670...")
i2c = I2C(0, freq=400_000, scl=Pin(scl_pin_no), sda=Pin(sda_pin_no))

try:
    ov7670 = OV7670Wrapper(
        i2c_bus=i2c,
        mclk_pin_no=mclk_pin_no,
        pclk_pin_no=pclk_pin_no,
        data_pin_base=data_pin_base,
        vsync_pin_no=vsync_pin_no,
        href_pin_no=href_pin_no,
        reset_pin_no=reset_pin_no,
        shutdown_pin_no=shutdown_pin_no,
    )
    ov7670.wrapper_configure_rgb()
    ov7670.wrapper_configure_base()
    width, height = ov7670.wrapper_configure_size(OV7670_WRAPPER_SIZE_DIV4)
    i2c.writeto_mem(0x21, 0x13, b'\xE7') 
    ov7670.wrapper_configure_test_pattern(OV7670_WRAPPER_TEST_PATTERN_NONE)

    print(f"✅ OV7670 initialized. Resolution: {width}x{height}")
    frame_buf = bytearray(width * height * 2) 
    gc.collect() 
except Exception as e:
    print(f"❌ Error initializing camera: {e}")
    sys.exit(1)

# Modified send_image_to_flash to include sequence number
def send_image_to_flash(image_data_buffer, img_width, img_height, seq_num):
    UPLOAD_URL = f"{FLASH_SERVER_URL}{UPLOAD_ENDPOINT}"

    full_raw_image_data = img_width.to_bytes(2, 'big') + \
                          img_height.to_bytes(2, 'big') + \
                          image_data_buffer

    headers = {
        "Content-Type": "application/octet-stream",
        "X-Device-IP": DEVICE_IP,
        "X-Image-Sequence": str(seq_num) # Add the sequence number here
    }

    for attempt in range(RETRY_ATTEMPTS):
        print(f"📤 Sending {len(full_raw_image_data)} bytes (Seq: {seq_num}) to {UPLOAD_URL}... (Attempt {attempt + 1}/{RETRY_ATTEMPTS})")
        try:
            response = requests.post(UPLOAD_URL, data=full_raw_image_data, headers=headers, timeout=TIMEOUT_SECONDS)
            if response.status_code == 200 or response.status_code == 201:
                try:
                    json_data = ujson.loads(response.text)
                except Exception as e:
                    print(f"❌ Error parsing JSON response: {e}")
                    response.close()
                    return None
                response.close()
                return json_data
            else:
                print(f"❌ Error sending. HTTP Code: {response.status_code}")
                response.close()
                if attempt < RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    return None
        except Exception as e:
            print(f"❌ Connection error: {e}")
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                return None
    return None

# Continuous capture and send
if __name__ == "__main__":
    gc.collect()
    while True:
        print("\n--- Capturing image ---")
        ov7670.capture(frame_buf) 
        print("✅ Image captured.")

        # Increment sequence number for each capture
        image_sequence_number += 1 
        print(f"💡 Assigning sequence number: {image_sequence_number}")

        # Pass the sequence number to the sending function
        resp = send_image_to_flash(frame_buf, width, height, image_sequence_number)
        if resp:
            print(f"✅ Server response: {resp}")
        else:
            print("❌ Could not send image.")

        time.sleep(2)