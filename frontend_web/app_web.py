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


