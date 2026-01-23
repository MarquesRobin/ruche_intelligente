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

# Paramètre pour la connexion à la base de données PostgreSQL
BD_NAME = os.getenv("POSTGRES_DB", "ruche_db")
BD_USER = os.getenv("POSTGRES_USER", "apiculteur")
BD_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password_pfe")
BD_HOST = os.getenv("POSTGRES_HOST", "database")

sql_create_table = """
CREATE TABLE IF NOT EXISTS mesures_ruche (
    id SERIAL PRIMARY KEY,
    date_heure TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    temperature NUMERIC(5,2),
    poids NUMERIC(6,3)
);
"""

try:
    with psycopg2.connect(
        dbname=BD_NAME, 
        user=BD_USER, 
        password=BD_PASSWORD, 
        host=BD_HOST
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_create_table)

except psycopg2.OperationalError:
    print("Erreur de connexion à la base de données : {e}")
else:
    print("Connexion à la base de données réussie et création de la table.")
finally:
    print("Fin de la procédure de connexion.")

