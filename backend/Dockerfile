# Image de base optimisée pour la taille
FROM python:3.9-slim

# Définition du répertoire de travail
WORKDIR /app

# Installation des dépendances système nécessaires (ex: pour psycopg2)
# RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances Python (optimisation du cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'intégralité du code source
COPY . .

# Exécution du script
CMD ["python", "app.py"]