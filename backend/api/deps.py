from fastapi import Depends, HTTPException, status, Request
from backend.core.database import get_db
from backend.core.config import settings
from backend.core.logger import logger
from datetime import datetime

async def get_current_user(request: Request):
    token = request.cookies.get("__session")
    if not token:
        # Check header if cookie missing
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        logger.warning("Authentication token not found in cookie or header.")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    session_ref = db.collection('Sessions').document(token)
    session = session_ref.get()
    
    if not session.exists:
        logger.warning(f"Session not found or expired: {token[:8]}...")
        raise HTTPException(status_code=401, detail="Session invalid")
    
    session_data = session.to_dict()
    expires_at = session_data.get('ExpiresAt')
    
    if expires_at:
        if expires_at.replace(tzinfo=None) < datetime.now():
            logger.warning(f"Session expired for token: {token[:8]}...")
            session_ref.delete()
            raise HTTPException(status_code=401, detail="Session expired")
    
    line_id = session_data.get('LineId')
    user_ref = db.collection('Users').document(line_id)
    user = user_ref.get()
    
    if not user.exists:
        logger.error(f"AUTH_ERROR: User document missing in Firestore for LineId: {line_id}")
        raise HTTPException(status_code=404, detail=f"User profile not found for ID: {line_id}")
        
    user_data = user.to_dict()
    user_data['LineId'] = line_id
    return user_data

async def get_current_admin(request: Request):
    # Logic to check if user is admin
    pass
