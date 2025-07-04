import time
from ClaseCentralPoo import CentralWiFi

# Inicializar clase central (ya no necesita SSID ni contraseña)
central = CentralWiFi(port=1234)

# Bucle principal del servidor
while True:
    # Recibir mensaje
    ip_remitente, puerto_remitente, datos_recibidos = central.recibir_mensaje()
    print("📦 Datos recibidos correctamente:", datos_recibidos)
    mensaje_respuesta = central.get_json_prueba()
    mensaje_respuesta1 = central.get_json_prueba1()
    mensaje_respuesta2 = central.get_json_prueba2()
    mensaje_respuesta3 = central.get_json_prueba3()
    mensaje_respuesta4 = central.get_json_prueba4()
    mensaje_respuesta5 = central.get_json_prueba5()
    mensaje_respuesta6 = central.get_json_prueba6()
    mensaje_respuesta7 = central.get_json_prueba7()
    mensaje_respuesta8 = central.get_json_prueba8()
    mensaje_respuesta9 = central.get_json_prueba9()
    mensaje_respuesta10 = central.get_json_prueba10()
    mensaje_respuesta11 = central.get_json_prueba11()
    mensaje_respuesta12 = central.get_json_prueba12()
    mensaje_respuesta13 = central.get_json_prueba13()
    central.enviar_json_a_dispositivo("192.168.0.111", 5525, mensaje_respuesta1) #David
    central.enviar_json_a_dispositivo("192.168.0.112", 5555, mensaje_respuesta2) #juan
    central.enviar_json_a_dispositivo("192.168.0.113", 5515, mensaje_respuesta3)
    central.enviar_json_a_dispositivo("192.168.0.114", 5557, mensaje_respuesta4) #alex y samuso
    central.enviar_json_a_dispositivo("192.168.0.121", 5569, mensaje_respuesta5) #Andres
    central.enviar_json_a_dispositivo("192.168.0.122", 5579, mensaje_respuesta6) #brayan
    central.enviar_json_a_dispositivo("192.168.0.123", 5589, mensaje_respuesta7) 
    central.enviar_json_a_dispositivo("192.168.0.128", 5599, mensaje_respuesta8)
    central.enviar_json_a_dispositivo("192.168.0.150", 5551, mensaje_respuesta9) #Anne 
    central.enviar_json_a_dispositivo("192.168.0.165", 5165, mensaje_respuesta10) #Luis
    central.enviar_json_a_dispositivo("192.168.0.115", 5557, mensaje_respuesta11) #carlos
    central.enviar_json_a_dispositivo("192.168.0.185", 5185, mensaje_respuesta12)  #bayona
    central.enviar_json_a_dispositivo("192.168.0.195", 5195, mensaje_respuesta13) #junior
    
    print("enviado")
    # Si hay datos recibidos, procesarlos y responder
    #if datos_recibidos:
        
        
        # Preparar y enviar respuesta a dispositivos específicos
        
    # Dormir un poco antes de la siguiente iteración
    time.sleep(2)
 