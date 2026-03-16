import serial
import time
import json
import paho.mqtt.client as mqtt
import re
import os

# Configuration matérielle
PORT_MATERIEL = os.getenv("LORA_PORT", "/dev/ttyUSB0")
BAUDRATE = 9600

# Configuration MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "ruche/mesures")

# Compilation de l'expression régulière pour extraire la charge hexadécimale
REGEX_WIO_RX = re.compile(r'\+TEST:\s*RX\s*"([A-F0-9]+)"')

def initialiser_mqtt():
    """Initialise le client MQTT en mode publication asynchrone."""
    client_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
    client_mqtt.loop_start()
    return client_mqtt

def traiter_trame(trame_hex, client_mqtt):
    """Décode l'hexadécimal et publie le JSON sur le broker."""
    try:
        chaine_ascii = bytes.fromhex(trame_hex).decode('ascii')
        donnees = chaine_ascii.split(';')
        
        if len(donnees) == 2:
            payload_json = {
                "temperature": float(donnees[0]),
                "poids": float(donnees[1])
            }
            client_mqtt.publish(MQTT_TOPIC, json.dumps(payload_json))
            print(f"Publication MQTT réussie : {payload_json}", flush=True)
        else:
            print("Rejet : Délimiteurs discordants dans la trame ASCII.", flush=True)
            
    except ValueError as erreur_typage:
        print(f"Exception de décodage ou de coercition de type : {erreur_typage}", flush=True)

def execution_passerelle():
    """Boucle principale d'acquisition UART."""
    client_mqtt = initialiser_mqtt()
    try:
        port_rx = serial.Serial(PORT_MATERIEL, baudrate=BAUDRATE, timeout=1)
        print(f"Interface matérielle {PORT_MATERIEL} ouverte.", flush=True)
        
        while True:
            if port_rx.in_waiting > 0:
                ligne_brute = port_rx.readline()
                try:
                    trame_uart = ligne_brute.decode('ascii').strip()
                    correspondance = REGEX_WIO_RX.search(trame_uart)
                    if correspondance:
                        traiter_trame(correspondance.group(1), client_mqtt)
                except UnicodeDecodeError:
                    pass
            time.sleep(0.05)
            
    except serial.SerialException as erreur_io:
        print(f"Défaillance du sous-système TTY : {erreur_io}", flush=True)

if __name__ == "__main__":
    execution_passerelle()