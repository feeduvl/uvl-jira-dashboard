# Verwenden Sie das offizielle Python-Image als Basis
FROM python:3.8

# Setzen Sie das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopieren Sie die Anforderungen in das Arbeitsverzeichnis
COPY requirements.txt requirements.txt

# Installieren Sie die Python-Abhängigkeiten
RUN pip install -r requirements.txt

# Kopieren Sie den restlichen Anwendungscode in das Arbeitsverzeichnis
COPY . .

# Definieren Sie den Befehl, um Ihre Flask-Anwendung auszuführen
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "9647"]
