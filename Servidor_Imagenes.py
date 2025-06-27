from flask import Flask, request, jsonify
import os
import threading
from datetime import datetime
import cv2
import numpy as np
from collections import defaultdict
import json

app = Flask(__name__)

# Directories for saving images
IMAGE_DIR = r"C:\Users\Public\Downloads\ov7670\imagenes" # Not used directly for saving in this version
PROCESSED_DIR = r"C:\Users\Public\Downloads\ov7670\procesadas"

# Create directories if they don't exist
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Global dictionary to store image counters for each IP address (as a fallback or for other clients)
image_counters = defaultdict(int)
# File to persist counters, so they don't reset on server restart
COUNTERS_FILE = os.path.join(PROCESSED_DIR, "server_image_counters.json") 

# Lock for thread-safe access to image_counters (if fallback is used)
lock = threading.Lock()

# Load existing counters on server startup
if os.path.exists(COUNTERS_FILE):
    try:
        with open(COUNTERS_FILE, 'r') as f:
            loaded_counters = json.load(f)
            for k, v in loaded_counters.items():
                image_counters[k] = v
        print(f"Contadores cargados: {dict(image_counters)}")
    except json.JSONDecodeError:
        print("Warning: Counters file corrupted or empty. Starting counters from scratch.")
    except Exception as e:
        print(f"Error loading counters: {e}")

# --- Image Processing Functions ---

def rgb565_to_rgb888(rgb565_bytes):
    """
    Converts 16-bit RGB565 raw image bytes to 24-bit RGB888.
    Output is in BGR format, which is standard for OpenCV.
    """
    result = bytearray()
    for i in range(0, len(rgb565_bytes), 2):
        pixel = (rgb565_bytes[i] << 8) | rgb565_bytes[i+1] 
        r = (pixel >> 11) & 0x1F 
        g = (pixel >> 5) & 0x3F  
        b = pixel & 0x1F       
        
        r = (r << 3) | (r >> 2)
        g = (g << 2) | (g >> 4)
        b = (b << 3) | (b >> 2)
        
        result.extend([b, g, r]) 
    return bytes(result)

def process_and_save_image(width, height, rgb888_data, device_ip, sequence_number_from_client=None):
    """
    Processes RGB888 image data, saves it as a JPG file,
    and names it using the device's IP and either its provided sequence number
    or a server-generated sequential number.
    """
    print(f"[🧠 Processing and Saving] Image from {width}x{height} from {device_ip}")

    np_image = np.frombuffer(rgb888_data, dtype=np.uint8).reshape((height, width, 3))
    
    # Determine the sequence number to use for the filename
    current_sequence_number = sequence_number_from_client
    if current_sequence_number is None:
        # If no sequence number from client, use server's internal counter (and increment it)
        with lock:
            image_counters[device_ip] += 1
            current_sequence_number = image_counters[device_ip]
            # Save updated counters to file
            try:
                with open(COUNTERS_FILE, 'w') as f:
                    json.dump(dict(image_counters), f)
            except Exception as e:
                print(f"❌ Error saving counters: {e}")
        print(f"💡 No sequence number from client, using server-generated: {current_sequence_number}")
    else:
        print(f"💡 Using client-provided sequence number: {current_sequence_number}")

    # Generate filename using sanitized IP and the determined sequence number
    sanitized_ip = device_ip.replace('.', '-') 
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
    
    # Construct the full filename (e.g., 192-168-0-200_0001_YYYYMMDD_HHMMSS.jpg)
    processed_filename_jpg = f"{sanitized_ip}_{int(current_sequence_number):04d}_{timestamp}.jpg"
    processed_path = os.path.join(PROCESSED_DIR, processed_filename_jpg)
    
    # Save the processed image (JPG) using OpenCV
    try:
        success = cv2.imwrite(processed_path, np_image)
        if not success:
            print(f"[⚠️ Error] Could not save processed image to {processed_path}")
            return
        print(f"[✔️ Image processed] Saved to: {processed_path}")
    except Exception as e:
        print(f"[❌ Error] Failed to save image {processed_path}: {e}")

# --- Flask App Endpoints ---

@app.route("/upload_raw_image_flash/", methods=["POST"])
def upload_image():
    """
    Endpoint to receive raw image data from the Raspberry Pi Pico W.
    It expects the device's IP in the 'X-Device-IP' header and
    the sequence number in the 'X-Image-Sequence' header.
    """
    device_ip = request.headers.get("X-Device-IP", request.remote_addr)
    # Get sequence number from header; convert to int. If not present, it's None.
    image_sequence = request.headers.get("X-Image-Sequence")
    if image_sequence:
        try:
            image_sequence = int(image_sequence)
        except ValueError:
            print(f"[⚠️ Warning] Invalid X-Image-Sequence header: {image_sequence}. Treating as None.")
            image_sequence = None # Fallback if header is present but not a valid integer

    print(f"📡 Image received from: {device_ip}, Sequence: {image_sequence if image_sequence is not None else 'N/A'}")

    data = request.get_data() 
    
    if len(data) < 4:
        print("[❌ Error] Insufficient data received.")
        return jsonify({"status": "error", "message": "Insuficiente data."}), 400

    width = int.from_bytes(data[0:2], 'big')
    height = int.from_bytes(data[2:4], 'big')
    image_data_rgb565 = data[4:] 

    expected_size = width * height * 2 
    if len(image_data_rgb565) != expected_size:
        print(f"[❌ Error] Invalid image data size. Expected: {expected_size}, Received: {len(image_data_rgb565)}")
        return jsonify({"status": "error", "message": f"Tamaño de datos inválido. Esperado {expected_size} bytes, recibido {len(image_data_rgb565)} bytes."}), 400

    rgb888_data = rgb565_to_rgb888(image_data_rgb565)
    
    # Pass the client-provided sequence number to the processing function
    threading.Thread(target=process_and_save_image, 
                     args=(width, height, rgb888_data, device_ip, image_sequence), 
                     daemon=True).start()

    return jsonify({
        "status": "ok",
        "device_ip": device_ip,
        "sequence_number": image_sequence,
        "message": "Imagen recibida y procesamiento iniciado en segundo plano."
    })

if __name__ == "__main__":
    print(f"Starting Flask server on http://0.0.0.0:8000")
    print(f"Processed images (JPG) will be saved in: {PROCESSED_DIR}")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)