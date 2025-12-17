import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "KKC Devotion System"
    API_V1_STR: str = "/api/v1"
    
    # Firestore / Firebase
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Frontend URL (For Callback construction)
    # Default to localhost for dev, but CAN be overridden in Cloud Run env vars
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000")

    # LINE
    LINE_CHANNEL_ID: str = os.getenv("LINE_CHANNEL_ID", "")
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")
    LINE_LIFF_ID: str = os.getenv("LINE_LIFF_ID", "")

    class Config:
        case_sensitive = True

settings = Settings()
