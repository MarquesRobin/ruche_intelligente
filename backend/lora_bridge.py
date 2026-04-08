# ========================================
# Auteur: Robin Marques
# Langage: Python
# 
# Description: Backend pour la passerelle de communication entre les capteurs LoRa et le broker MQTT.
# Ce script lit les données reçues via le port série, les traite et les publie sur un topic MQTT pour être consommées par le backend principal.
# =========================================

import serial
import time
import json
import math
import paho.mqtt.client as mqtt
import re
import os

PORT_MATERIEL = os.getenv("LORA_PORT", "/dev/ttyUSB0")
BAUDRATE = 9600
MQTT_BROKER = os.getenv("MQTT_BROKER", "hive_mqtt_broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "ruche/mesures")

REGEX_WIO_RX = re.compile(r'\+TEST:\s*RX\s*"([A-F0-9]+)"')

def initialiser_mqtt():
    client_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
        client_mqtt.loop_start()
        print(f"Connexion MQTT établie vers {MQTT_BROKER}", flush=True)
    except Exception as e:
        print(f"Erreur de résolution MQTT : {e}", flush=True)
    return client_mqtt

def traiter_trame(trame_hex, client_mqtt):
    try:
        chaine_ascii = bytes.fromhex(trame_hex).decode('ascii')
        print(f"-> Décodage ASCII réussi : {chaine_ascii}", flush=True)
        donnees = chaine_ascii.split(';')

        # Validation stricte du vecteur à 7 dimensions (Température;Humidité;Fréquence;Poids;SoC;Latitude;Longitude)
        if len(donnees) == 7:
            def parse(s):
                val = float(s)
                return None if math.isnan(val) else val

            payload_json = {
                "temperature": parse(donnees[0]),
                "humidite":    parse(donnees[1]),
                "frequence":   parse(donnees[2]),
                "poids":       parse(donnees[3]),
                "soc":         parse(donnees[4]),
                "latitude":    parse(donnees[5]),
                "longitude":   parse(donnees[6])
            }
            client_mqtt.publish(MQTT_TOPIC, json.dumps(payload_json))
            print(f"-> Publication MQTT réussie : {payload_json}", flush=True)
        else:
            print(f"-> Rejet analytique : Dimension vectorielle incorrecte ({len(donnees)} au lieu de 7).", flush=True)

    except ValueError as erreur_typage:
        print(f"-> Exception de coercition typologique : {erreur_typage}", flush=True)

def initialiser_module_lora(port_rx):
    """Séquence d'échappement matérielle avec validation d'acquittement."""
    print("Synchronisation matérielle (Attente de fin d'amorçage MCU)...", flush=True)
    # Délai critique pour permettre au microcontrôleur de terminer son démarrage après l'ouverture du port série
    time.sleep(2.0) 
    port_rx.reset_input_buffer()
    
    commandes_radio = [
        b'AT\r\n',
        b'AT+MODE=TEST\r\n',
        b'AT+TEST=RFCFG,915000000,12,125,8,14,ON,OFF,OFF\r\n',
        b'AT+TEST=RXLRPKT\r\n'
    ]
    
    for commande in commandes_radio:
        port_rx.write(commande)
        time.sleep(0.5) # Temps de traitement de la commande par le firmware
        
        # Capture synchrone de la réponse d'état
        if port_rx.in_waiting > 0:
            reponse = port_rx.read(port_rx.in_waiting).decode('ascii', errors='ignore').replace('\r\n', ' ')
            print(f"[TX] {commande.decode('ascii').strip()} -> [RX] {reponse.strip()}", flush=True)
        else:
            print(f"[TX] {commande.decode('ascii').strip()} -> [RX] ECHEC: DELAI DE REPONSE DEPASSE", flush=True)
            
    print("Séquence d'initialisation AT terminée.", flush=True)

def execution_passerelle():
    client_mqtt = initialiser_mqtt()

    while True:
        try:
            port_rx = serial.Serial()
            port_rx.port = PORT_MATERIEL
            port_rx.baudrate = BAUDRATE
            port_rx.timeout = 1
            port_rx.dtr = False
            port_rx.rts = False
            
            port_rx.open()
            
            with port_rx:
                initialiser_module_lora(port_rx)
                
                while True:
                    if port_rx.in_waiting > 0:
                        ligne_brute = port_rx.readline().decode('ascii', errors='ignore').strip()
                        
                        if ligne_brute:
                            correspondance = REGEX_WIO_RX.search(ligne_brute)
                            if correspondance:
                                trame_hex = correspondance.group(1)
                                traiter_trame(trame_hex, client_mqtt)
                            elif "+TEST" not in ligne_brute and "OK" not in ligne_brute:
                                print(f"[BRUIT SERIE] : {ligne_brute}", flush=True)
                                
        except serial.SerialException as e:
            print(f"Erreur d'état TTY : {e}. Reconnexion dans 5s...", flush=True)
            time.sleep(5)
        except OSError as e:
            print(f"Exception matérielle d'E/S : {e}. Reconnexion dans 5s...", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    execution_passerelle()