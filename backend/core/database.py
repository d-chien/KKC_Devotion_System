import firebase_admin
from firebase_admin import credentials, firestore
from backend.core.config import settings
import os

db = None

def get_db():
    global db
    if db is None:
        # Check if credentials file exists, otherwise assume implicit environment (Cloud Run/Functions)
        if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(cred)
        else:
            # For Cloud Run, use default credentials or check if app is already init
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app()
        
        try:
            # Use environment variable for database name if provided, else default to (default)
            db_name = os.getenv("FIRESTORE_DATABASE", "devotion-system")
            
            if db_name == "(default)":
                db = firestore.client()
            else:
                from google.cloud import firestore as google_firestore
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT', os.getenv('GCP_PROJECT_ID'))
                db = google_firestore.Client(project=project_id, database=db_name)
            
            print(f"Successfully connected to Firestore DB: {db_name}")
        except Exception as e:
            print(f"Failed to connect to Firestore. Error: {e}")
            db = firestore.client()
    return db
