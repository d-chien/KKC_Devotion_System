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
        
        # Connect to the specific database 'devotion-system'
        # Note: If accessing 'default', no argument is needed.
        try:
             # Try connecting with database ID (requires newer library versions or generic client)
             # The firebase_admin.firestore.client() helper usually connects to (default).
             # To connect to a named db, we might need to pass it.
             # However, the python firebase-admin SDK wraps google-cloud-firestore.
             # We pass the `database` argument to he client constructor if possible, 
             # but `firestore.client()` is a helper.
             
             # Correct way for named DB in newer SDKs:
             db = firestore.client(database='devotion-system')
        except TypeError:
             # Fallback if SDK version is old (though requirements.txt has recent one)
             db = firestore.client()
    return db
