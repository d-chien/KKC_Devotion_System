from fastapi import Depends, HTTPException, status, Request
from backend.core.database import get_db
from backend.core.config import settings
from backend.core.logger import logger

async def get_current_user(request: Request):
    token = request.cookies.get("__session")
    if not token:
        # Check header if cookie missing
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_db()
    session_ref = db.collection('Sessions').document(token)
    session = session_ref.get()
    
    if not session.exists:
        logger.warning(f"Session not found or expired: {token[:8]}...")
        raise HTTPException(status_code=401, detail="Session invalid")
    
    session_data = session.to_dict()
    line_id = session_data.get('LineId')
    
    user_ref = db.collection('Users').document(line_id)
    user = user_ref.get()
    
    if not user.exists:
        print(f"DEBUG: User not found in 'Users' collection for LineId: {line_id}")
        raise HTTPException(status_code=404, detail=f"User {line_id} not found")
        
    user_data = user.to_dict()
    user_data['LineId'] = line_id # Inject ID
    return user_data

async def get_current_admin(request: Request):
    # Logic to check if user is admin
    pass
