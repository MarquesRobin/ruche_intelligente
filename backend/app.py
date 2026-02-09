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