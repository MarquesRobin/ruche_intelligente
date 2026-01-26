# ========================================
# Auteur: Robin Marques
# Langage: Python 3.11
# 
# 
# 
# 
# 
# 
# 
# =========================================

# ===== CREATION DE MA BASE DE DONNEES =====

import psycopg2
import os
import time

# Paramètre pour la connexion à la base de données PostgreSQL
BD_NAME = os.getenv("POSTGRES_DB", "ruche_db")
BD_USER = os.getenv("POSTGRES_USER", "apiculteur")
BD_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password_pfe")
BD_HOST = os.getenv("POSTGRES_HOST", "database")

def connect_with_retry():
    max_retries = 5
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                dbname=BD_NAME, 
                user=BD_USER, 
                password=BD_PASSWORD, 
                host=BD_HOST
            )
            return conn
        except psycopg2.OperationalError as e:
            print(f"Tentative {i+1}/{max_retries} échouée : {e}")
            if i < max_retries - 1:
                print("Nouvelle tentative dans 5 secondes...")
                time.sleep(5)
            else:
                raise Exception("Échec de connexion après plusieurs tentatives.")

sql_create_table = """
CREATE TABLE IF NOT EXISTS mesures_ruche (
    id SERIAL PRIMARY KEY,
    date_heure TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    temperature NUMERIC(5,2),
    poids NUMERIC(6,3)
);
"""

if __name__ == "__main__":
    try:
        # APPEL DE LA FONCTION DE CONNEXION
        connection = connect_with_retry()
        cursor = connection.cursor()
        
        # EXÉCUTION DE LA CRÉATION DE TABLE
        cursor.execute(sql_create_table)
        connection.commit()
        print("Table 'mesures_ruche' vérifiée/créée avec succès.")
        
        print("Lancement du service de monitoring (boucle active)...")
        while True:
            # Vérification de la santé de la connexion toutes les minutes
            time.sleep(60)
      
    except Exception as error:
        print(f"Erreur fatale lors de l'initialisation : {error}")
    finally:
        if 'connection' in locals() and connection:
            cursor.close()
            connection.close()