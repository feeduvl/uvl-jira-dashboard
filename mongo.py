import os

from pymongo import MongoClient


class MongoDB:
    def __init__(self, port=27017):
        is_testing = os.environ.get("FLASK_ENV") == "test"

        # Wählen Sie den MongoDB-Host basierend auf der Umgebung
        self.host = "localhost" if is_testing else "mongo"
        # MongoDB-Verbindung initialisieren
        self.client = MongoClient(f"mongodb://{self.host}:{port}/")

        # Datenbank und Sammlungen initialisieren
        self.db_issues = self.client["jira_dashboard"]
        self.collection_jira_issues = self.db_issues["jira_issue"]
        #self.collection_imported_feedback = self.db_issues["imported_feedback"]
        self.collection_assigned_feedback = self.db_issues["assigned_feedback"]
        self.collection_saved_data = self.db_issues["saved_data"]

        self.db_feedback = self.client["concepts_data"]
        self.collection_feedback = self.db_feedback["dataset"]
        self.collection_annotations = self.db_feedback["annotation"]


mongo_db = MongoDB()
