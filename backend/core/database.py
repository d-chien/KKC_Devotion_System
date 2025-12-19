import firebase_admin
from firebase_admin import credentials, firestore
from backend.core.config import settings
import os
from backend.core.logger import logger
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
            # Consistent database selection
            db_name = os.getenv("FIRESTORE_DATABASE", "devotion-system")
            logger.info(f"Connecting to Firestore: Project={os.getenv('GOOGLE_CLOUD_PROJECT')}, Database={db_name}")
            
            if db_name == "(default)":
                db = firestore.client()
            else:
                from google.cloud import firestore as google_firestore
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT', os.getenv('GCP_PROJECT_ID'))
                
                client_kwargs = {"project": project_id, "database": db_name}
                if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                    from google.oauth2 import service_account
                    client_kwargs["credentials"] = service_account.Credentials.from_service_account_file(
                        settings.FIREBASE_CREDENTIALS_PATH
                    )
                db = google_firestore.Client(**client_kwargs)
            
            logger.info(f"Successfully connected to Firestore DB: {db_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Firestore DB {db_name}: {e}")
            db = firestore.client()
    return db
