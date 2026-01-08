# Projet : La Ruche Intelligente
Ce dépôt centralise l'ensemble des développements logiciels et micrologiciels pour le système de télésurveillance apicole autonome. 

## Architecture du Répertoire
* **`/firmware`** : Codes sources pour les microcontrôleurs ESP32 et STM32 chargés de l'acquisition des données capteurs (poids, température, humidité, acoustique).
* **`/backend`** : Serveur de traitement, API REST (FastAPI/Flask) et script de transfert de données MQTT vers PostgreSQL.
* **`/frontend_web`** : Interface utilisateur pour navigateur basée sur Jinja2 et Flask.
* **`/mobile_app`** : Application mobile multiplateforme développée avec Flutter.
* **`/infrastructure`** : Fichiers de configuration Docker pour l'orchestration du broker MQTT Mosquitto et de la base de données PostgreSQL.

## Installation Rapide
1. Installer Docker Desktop.
2. Naviguer dans `/infrastructure`.
3. Lancer les services : `docker-compose up -d`.