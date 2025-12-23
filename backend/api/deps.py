from fastapi import Depends, HTTPException, status, Request
from backend.core.database import get_db
from backend.core.config import settings
from backend.core.logger import logger
from datetime import datetime

async def get_current_user(request: Request):
    """Dependency for public/user endpoints. Uses __session cookie."""
    token = request.cookies.get("__session")
    if not token:
        logger.warning("User session token not found.")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    session_doc = db.collection('Sessions').document(token).get()
    
    if not session_doc.exists:
        raise HTTPException(status_code=401, detail="Session invalid")
    
    session_data = session_doc.to_dict()
    # Check expiry
    expires_at = session_data.get('ExpiresAt')
    if expires_at and expires_at.replace(tzinfo=None) < datetime.now():
        raise HTTPException(status_code=401, detail="Session expired")

    # Strict Role Check
    if session_data.get('Role') != 'User':
        raise HTTPException(status_code=403, detail="Invalid session type for this area")

    line_id = session_data.get('LineId')
    user_doc = db.collection('Users').document(line_id).get()
    
    if not user_doc.exists:
        logger.error(f"User profile missing for {line_id}")
        raise HTTPException(status_code=404, detail="User profile not found")
        
    user_data = user_doc.to_dict()
    user_data['LineId'] = line_id
    return user_data

async def get_current_admin(request: Request):
    """Dependency for admin endpoints. Uses __session cookie."""
    token = request.cookies.get("__session")
    if not token:
        logger.warning("Admin session token not found.")
        raise HTTPException(status_code=401, detail="Admin authentication required")
    
    db = get_db()
    session_doc = db.collection('Sessions').document(token).get()
    
    if not session_doc.exists:
        raise HTTPException(status_code=401, detail="Admin session invalid")
    
    session_data = session_doc.to_dict()
    
    # Strict Role Check
    if session_data.get('Role') != 'Admin':
        logger.warning(f"Non-admin session tried to access admin area: {token[:8]}")
        raise HTTPException(status_code=403, detail="Admin role required")

    return {
        "LineId": session_data.get('LineId'),
        "Role": "Admin"
    }

