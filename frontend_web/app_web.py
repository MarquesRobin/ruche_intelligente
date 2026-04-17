# ========================================
# Auteur: Robin Marques
# Langage: Python 3.11
#
# Description: Frontend web pour la visualisation des données des ruches intelligentes.
# Expose 3 pages : données principales (température, humidité, poids),
# fréquence acoustique, et localisation GPS.
# =========================================

import psycopg2
from flask import Flask, render_template
import os
import json
from zoneinfo import ZoneInfo

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "ruche_db"),
        user=os.getenv("POSTGRES_USER", "apiculteur"),
        password=os.getenv("POSTGRES_PASSWORD", "password_pfe"),
        port=5432
    )
    return conn

def get_mesures():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date_heure, temperature, humidite, frequence, poids, soc, latitude, longitude
        FROM (
            SELECT * FROM mesures_ruche ORDER BY date_heure DESC LIMIT 300
        ) AS dernieres
        ORDER BY date_heure ASC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

UTC      = ZoneInfo('UTC')
QUEBEC   = ZoneInfo('America/Toronto')

def to_float(val):
    return float(val) if val is not None else None

def fmt_date(dt):
    return dt.replace(tzinfo=UTC).astimezone(QUEBEC).strftime('%d/%m %H:%M:%S')

@app.route('/')
def home():
    try:
        mesures = get_mesures()
        labels       = [fmt_date(m[1]) for m in mesures]
        temperatures = [to_float(m[2]) for m in mesures]
        humidites    = [to_float(m[3]) for m in mesures]
        poids        = [round(to_float(m[5]) * 1000, 1) if to_float(m[5]) is not None else None for m in mesures]
        soc          = [to_float(m[6]) for m in mesures]
        return render_template('index.html',
            active_page='home',
            labels=json.dumps(labels),
            temperatures=json.dumps(temperatures),
            humidites=json.dumps(humidites),
            poids=json.dumps(poids),
            soc=json.dumps(soc)
        )
    except Exception as e:
        return f"Erreur de connexion à la base de données : {e}"

@app.route('/frequence')
def frequence():
    try:
        mesures = get_mesures()
        labels     = [fmt_date(m[1]) for m in mesures]
        frequences = [to_float(m[4]) for m in mesures]
        return render_template('frequence.html',
            active_page='frequence',
            labels=json.dumps(labels),
            frequences=json.dumps(frequences)
        )
    except Exception as e:
        return f"Erreur de connexion à la base de données : {e}"

@app.route('/gps')
def gps():
    try:
        mesures = get_mesures()
        points = [
            {
                'date': fmt_date(m[1]),
                'lat': to_float(m[7]),
                'lon': to_float(m[8]),
            }
            for m in mesures
            if m[7] is not None and m[8] is not None
        ]
        return render_template('gps.html',
            active_page='gps',
            points=points
        )
    except Exception as e:
        return f"Erreur de connexion à la base de données : {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
