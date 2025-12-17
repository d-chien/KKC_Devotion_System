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
            # Explicitly use google-cloud-firestore client to ensure database selection works
            from google.cloud import firestore as google_firestore
            
            # Get project ID from environment or settings
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT', os.getenv('GCP_PROJECT_ID'))
            
            if not project_id and settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                 # derive from credentials if not in env
                 pass 

            # Initialize Client directly
            # This is more robust for named databases than firebase_admin wrapper in some versions
            db = google_firestore.Client(
                project=project_id,
                database='devotion-system'
            )
            print(f"Successfully connected to Firestore DB: devotion-system in project {project_id}")
        except Exception as e:
            print(f"Failed to connect to named DB, falling back to default. Error: {e}")
            # Fallback
            db = firestore.client()
    return db
