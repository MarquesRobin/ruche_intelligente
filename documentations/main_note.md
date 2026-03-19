app.py :

# ========================================
# Auteur: Robin Marques
# Langage: Python 3.11
# 
# Description: Backend pour la gestion des données des ruches intelligentes.
# Ce script se connecte à une base de données PostgreSQL pour stocker les mesures
# reçues via MQTT. Il crée la table nécessaire si elle n'existe pas déjà et
# gère la connexion au broker MQTT pour recevoir les données des capteurs.
# =========================================

# ========================================
# Auteur: Robin Marques
# Langage: Python 3.11
# =========================================

import psycopg2
import os
import time
import json
import paho.mqtt.client as mqtt

# CONFIGURATION
BD_NAME = os.getenv("POSTGRES_DB", "ruche_db")
BD_USER = os.getenv("POSTGRES_USER", "apiculteur")
BD_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password_pfe")
BD_HOST = os.getenv("POSTGRES_HOST", "database")

MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "ruche/mesures")

def insert_measure(temperature, poids):
    try:
        conn = psycopg2.connect(dbname=BD_NAME, user=BD_USER, password=BD_PASSWORD, host=BD_HOST)
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO mesures_ruche (temperature, poids) VALUES (%s, %s);",
                (temperature, poids)
            )
            conn.commit()
        conn.close()
        print(f"Insertion réussie : {temperature}°C | {poids}kg", flush=True)
    except Exception as e:
        print(f"Erreur d'insertion SQL : {e}", flush=True)

# INITIALISATION DU CLIENT (Version 2)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"Connecté au broker MQTT sur le topic : {MQTT_TOPIC}", flush=True)
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Erreur de connexion MQTT, code : {reason_code}", flush=True)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        temp = payload.get("temperature")
        poids = payload.get("poids")
        if temp is not None and poids is not None:
            insert_measure(temp, poids)
    except Exception as e:
        print(f"Erreur de décodage JSON : {e}", flush=True)

# On attache les fonctions de rappel (callbacks) au client
client.on_connect = on_connect
client.on_message = on_message

def connect_with_retry():
    max_retries = 5
    for i in range(max_retries):
        try:
            return psycopg2.connect(dbname=BD_NAME, user=BD_USER, password=BD_PASSWORD, host=BD_HOST)
        except psycopg2.OperationalError as e:
            print(f"Tentative de connexion DB {i+1}/{max_retries} échouée. DNS peut-être pas prêt...", flush=True)
            time.sleep(10)
    raise Exception("Base de données inaccessible.")

if __name__ == "__main__":
    try:
        print("Vérification de la structure de la base de données...", flush=True)
        conn_init = connect_with_retry()
        with conn_init.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mesures_ruche (
                    id SERIAL PRIMARY KEY,
                    date_heure TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    temperature NUMERIC(5,2),
                    poids NUMERIC(6,3)
                );
            """)
            conn_init.commit()
        conn_init.close()
        print("Table 'mesures_ruche' prête.", flush=True)

        print(f"Connexion au broker {MQTT_BROKER}...", flush=True)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        # loop_forever est bloquant, il maintient le conteneur actif
        client.loop_forever()

    except Exception as error:
        print(f"Erreur fatale du backend : {error}", flush=True)

Dockerfile :

FROM python:3.9-slim

WORKDIR /app

# Décommenté : Indispensable pour la compilation de psycopg2 sur architecture ARM (Raspberry Pi)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]





Dockerfile_gateway :

FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lora_bridge.py .

CMD ["python", "lora_bridge.py"]





lora_bridge.py :

import serial
import time
import json
import paho.mqtt.client as mqtt
import re
import os

# Configuration matérielle (Rétrogradation forcée pour diagnostic)
PORT_MATERIEL = os.getenv("LORA_PORT", "/dev/ttyUSB0")
BAUDRATE = 9600

# Configuration MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "ruche/mesures")

# Filtre d'extraction hexadécimale
REGEX_WIO_RX = re.compile(r'\+TEST:\s*RX\s*"([A-F0-9]+)"')

def initialiser_mqtt():
    """Instanciation du client MQTT asynchrone."""
    client_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
    client_mqtt.loop_start()
    return client_mqtt

def traiter_trame(trame_hex, client_mqtt):
    """Conversion de la charge utile et publication."""
    try:
        chaine_ascii = bytes.fromhex(trame_hex).decode('ascii')
        print(f"-> Décodage ASCII réussi : {chaine_ascii}", flush=True)
        donnees = chaine_ascii.split(';')
        
        if len(donnees) == 2:
            payload_json = {
                "temperature": float(donnees[0]),
                "poids": float(donnees[1])
            }
            client_mqtt.publish(MQTT_TOPIC, json.dumps(payload_json))
            print(f"-> Publication MQTT réussie : {payload_json}", flush=True)
        else:
            print(f"-> Rejet analytique : Délimiteurs discordants ({chaine_ascii})", flush=True)
            
    except ValueError as erreur_typage:
        print(f"-> Exception de coercition typologique : {erreur_typage}", flush=True)

def execution_passerelle():
    print("Initialisation de l'infrastructure logicielle MQTT...", flush=True)
    client_mqtt = initialiser_mqtt()

    while True:
        try:
            # 1. Instanciation à vide (sans ouverture immédiate)
            port_rx = serial.Serial()
            port_rx.port = PORT_MATERIEL
            port_rx.baudrate = BAUDRATE
            port_rx.timeout = 1
            
            # 2. Neutralisation des signaux de contrôle de flux (Auto-Reset)
            port_rx.dtr = False
            port_rx.rts = False
            
            # 3. Ouverture manuelle sécurisée du descripteur de fichier
            port_rx.open()
            
            # Le gestionnaire de contexte sécurise la fermeture en cas d'exception
            with port_rx:
                print(f"Interface matérielle {PORT_MATERIEL} synchronisée à {BAUDRATE} bauds (DTR/RTS neutralisés).", flush=True)
                
                while True:
                    if port_rx.in_waiting > 0:
                        ligne_brute = port_rx.readline().decode('ascii', errors='ignore').strip()
                        
                        if ligne_brute:
                            print(f"[DEBUG RAW] : {ligne_brute}", flush=True)
                            
                            correspondance = REGEX_WIO_RX.search(ligne_brute)
                            if correspondance:
                                trame_hex = correspondance.group(1)
                                traiter_trame(trame_hex, client_mqtt)
                            else:
                                print("-> [ECHEC REGEX] : Trame asymétrique ignorée.", flush=True)
                                
        except serial.SerialException as e:
            print(f"Erreur d'état TTY : {e}. Reconnexion dans 5s...", flush=True)
            time.sleep(5)
        except OSError as e:
            print(f"Exception matérielle d'E/S : {e}. Reconnexion dans 5s...", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    execution_passerelle()




requirements.txt :

paho-mqtt
psycopg2-binary
Flask
pyserial




index.html :

<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Dashboard Ruche Intelligente</title>
    <style>
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
    </style>
</head>
<body>
    <h1>Mesures des Ruches en Temps Réel</h1>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Date et Heure</th>
                <th>Température (°C)</th>
                <th>Poids (kg)</th>
            </tr>
        </thead>
        <tbody>
            {% for mesure in mesures %}
            <tr>
                <td>{{ mesure[0] }}</td>
                <td>{{ mesure[1] }}</td>
                <td>{{ mesure[2] }}</td>
                <td>{{ mesure[3] }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>



app_web.py :

import psycopg2
from flask import Flask, render_template
import os

app = Flask(__name__)

def get_db_connection():
    # Connexion à la base de données tournant dans Docker
    conn = psycopg2.connect(
        host='localhost', # 'localhost' car on l'appelle depuis le PC hôte
        database=os.getenv("POSTGRES_DB", "ruche_db"),
        user=os.getenv("POSTGRES_USER", "apiculteur"),
        password=os.getenv("POSTGRES_PASSWORD", "password_pfe"),
        port=5432
    )
    return conn

@app.route('/')
def home():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Récupération de toutes les mesures de la table
        cur.execute('SELECT id, date_heure, temperature, poids FROM mesures_ruche ORDER BY date_heure DESC;')
        mesures_db = cur.fetchall() # Récupère toutes les lignes
        cur.close()
        conn.close()
        return render_template('index.html', mesures=mesures_db)
    except Exception as e:
        return f"Erreur de connexion à la base de données : {e}"

if __name__ == '__main__':
    # host='0.0.0.0' permet l'accès réseau, debug=True facilite le développement
    app.run(host='0.0.0.0', port=8080, debug=True)




mosquitto.conf :

listener 1883
allow_anonymous true



docker-compose.yml :

# ----------------------------------------------
# title: docker-compose.yml
# author: Robin Marques
# date: 2026-01-07
# updated: 2026-02-17
# type: configuration
# status: active
# tags:
#   - docker
#
# description: Fichier de configuration Docker Compose pour déployer les services nécessaires à la gestion des ruches connectées.
# ----------------------------------------------

services:
  # ========== Services Docker Compose ==========
  #
  # Service de base de données PostgreSQL pour stocker les données des ruches.
  #
  # ============================================
  database:
    image: postgres:15
    container_name: hive_db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ruche_db
      POSTGRES_USER: apiculteur
      POSTGRES_PASSWORD: password_pfe
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U apiculteur -d ruche_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # ========= MQTT Broker Service ==========
  #
  # Service MQTT Broker utilisant Eclipse Mosquitto. 
  # Il gère la communication entre les capteurs des ruches et le backend.
  #
  # ========================================
  mqtt-broker:
    image: eclipse-mosquitto:latest
    container_name: hive_mqtt_broker
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config/mosquitto.conf:/mosquitto/config/mosquitto.conf
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    restart: always

  # ========= Backend API Service ==========
  #
  # Service backend API développé en Python avec Flask. Il traite les données reçues des capteurs et fournit une API RESTful.
  #
  # ========================================
  api_backend:
    build: 
      context: ../backend
      dockerfile: Dockerfile
    container_name: hive_api_backend
    ports:
      - "5000:5000"
    depends_on:
      mqtt-broker:
        condition: service_started
      database:
          condition: service_healthy
    restart: on-failure
    environment:
      - PYTHONUNBUFFERED=1
      - MQTT_BROKER=hive_mqtt_broker
      - POSTGRES_HOST=hive_db

# ========= LoRa Gateway Service ==========
  #
  # Service LoRa Gateway pour la communication avec les capteurs LoRa.
  #
  # ========================================

  lora_gateway:
   build: 
     context: ../backend # Même contexte que api_backend car lora_bridge.py y est stocké
     dockerfile: Dockerfile_gateway
   container_name: hive_lora_gateway
   devices:
     - "/dev/ttyUSB0:/dev/ttyUSB0"
   environment:
     - PYTHONUNBUFFERED=1
     - MQTT_BROKER=hive_mqtt_broker
   depends_on:
     - mqtt-broker
   restart: on-failure


volumes:
  postgres_data:





