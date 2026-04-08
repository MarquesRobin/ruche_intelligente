# ========================================
# Auteur: Robin Marques
# Langage: Python 3.11
# 
# Description: Backend pour la gestion des données des ruches intelligentes.
# Ce script se connecte à une base de données PostgreSQL pour stocker les mesures
# reçues via MQTT. Il crée la table nécessaire si elle n'existe pas déjà et
# gère la connexion au broker MQTT pour recevoir les données des capteurs.
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

def insert_measure(temperature, humidite, frequence, poids, soc, latitude, longitude):
    try:
        conn = psycopg2.connect(dbname=BD_NAME, user=BD_USER, password=BD_PASSWORD, host=BD_HOST)
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO mesures_ruche
                   (temperature, humidite, frequence, poids, soc, latitude, longitude)
                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (temperature, humidite, frequence, poids, soc, latitude, longitude)
            )
            conn.commit()
        conn.close()
        print(f"Insertion réussie : {temperature}°C | {humidite}% | {frequence}Hz | {poids}kg | SoC:{soc}% | ({latitude}, {longitude})", flush=True)
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
        temp      = payload.get("temperature")
        humidite  = payload.get("humidite")
        frequence = payload.get("frequence")
        poids     = payload.get("poids")
        soc       = payload.get("soc")
        latitude  = payload.get("latitude")
        longitude = payload.get("longitude")
        if any(v is not None for v in (temp, humidite, frequence, poids, soc, latitude, longitude)):
            insert_measure(temp, humidite, frequence, poids, soc, latitude, longitude)
        else:
            print(f"Payload entièrement vide, message ignoré : {payload}", flush=True)
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
                    id          SERIAL PRIMARY KEY,
                    date_heure  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    temperature NUMERIC(5,2),
                    humidite    NUMERIC(5,2),
                    frequence   NUMERIC(10,2),
                    poids       NUMERIC(6,3),
                    soc         NUMERIC(5,2),
                    latitude    NUMERIC(10,7),
                    longitude   NUMERIC(10,7)
                );
            """)
            # Migration : ajout des nouvelles colonnes si la table existait déjà
            nouvelles_colonnes = [
                ("humidite",  "NUMERIC(5,2)"),
                ("frequence", "NUMERIC(10,2)"),
                ("soc",       "NUMERIC(5,2)"),
                ("latitude",  "NUMERIC(10,7)"),
                ("longitude", "NUMERIC(10,7)"),
            ]
            for colonne, type_sql in nouvelles_colonnes:
                cursor.execute(f"""
                    ALTER TABLE mesures_ruche
                    ADD COLUMN IF NOT EXISTS {colonne} {type_sql};
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