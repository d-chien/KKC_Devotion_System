from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
import httpx
import uuid
from datetime import datetime, timedelta
from backend.core.config import settings
from backend.core.database import get_db
from backend.schemas import Token
from backend.api import deps
from backend.core.logger import logger
from backend.core.audit import record_audit_log
# Only import if you have deps specific logic, otherwise define here

router = APIRouter()

# LINE API URLs
LINE_AUTH_URL = 'https://access.line.me/oauth2/v2.1/authorize'
LINE_TOKEN_URL = 'https://api.line.me/oauth2/v2.1/token'
LINE_PROFILE_URL = 'https://api.line.me/v2/profile'

@router.get('/line/login')
async def line_login(request: Request):
    logger.debug("Starting LINE login flow")
    state = str(uuid.uuid4())
    scope = 'profile openid'
    
    # In a real app, store state in cookie to verify later
    
    # Use configured frontend URL as base to ensure consistency between
    # what the user sees (Firebase) and what the backend constructs.
    base_url = settings.FRONTEND_URL.rstrip('/')
    redirect_uri = f"{base_url}/api/auth/line/callback"

    params = {
        'response_type': 'code',
        'client_id': settings.LINE_CHANNEL_ID,
        'redirect_uri': redirect_uri,
        'state': state,
        'scope': scope,
        'prompt': 'consent'
    }
    
    # Construct URL manually or via httpx
    url = httpx.URL(LINE_AUTH_URL, params=params)
    print(url)
    return RedirectResponse(str(url))

@router.get('/line/callback', name='line_callback')
async def line_callback(request: Request, code: str, state: str, error: str = None, error_description: str = None):
    if error:
        logger.error(f"LINE login error: {error_description}")
        raise HTTPException(status_code=400, detail=error_description)
    
    logger.info(f"Received LINE callback with state: {state}")
    
    # Must match exactly the redirect_uri used in the login step
    base_url = settings.FRONTEND_URL.rstrip('/')
    redirect_uri = f"{base_url}/api/auth/line/callback"

    async with httpx.AsyncClient() as client:
        # Get Token
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': settings.LINE_CHANNEL_ID,
            'client_secret': settings.LINE_CHANNEL_SECRET
        }
        r = await client.post(LINE_TOKEN_URL, data=data)
        if r.status_code != 200:
             raise HTTPException(status_code=400, detail="Failed to get line token")
        token_data = r.json()
        access_token = token_data.get('access_token')
        
        # Get Profile
        r_profile = await client.get(LINE_PROFILE_URL, headers={'Authorization': f'Bearer {access_token}'})
        if r_profile.status_code != 200:
             raise HTTPException(status_code=400, detail="Failed to get user profile")
        profile = r_profile.json()
        line_id = profile.get('userId')
        display_name = profile.get('displayName')
        
        # DB Operations
        db = get_db()
        users_ref = db.collection('Users')
        # Query if user exists
        # Users structure: {LineId: { ... }} - Document ID should be LineId
        user_doc_ref = users_ref.document(line_id)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            # Create new user
            user_data = {
                'LineName': display_name,
                'BindDate': None, # Not bound yet
                'MemberId': None,
                'MemberName': None
            }
            user_doc_ref.set(user_data)
        else:
            # Update name if changed?
            pass
            
        # 0. Delete old sessions for this user
        sessions_ref = db.collection('Sessions')
        old_sessions = sessions_ref.where('LineId', '==', line_id).stream()
        for old_s in old_sessions:
            old_s.reference.delete()
            
        # Create Session
        session_token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=30)
        
        # Store session in Firestore
        sessions_ref = db.collection('Sessions')
        sessions_ref.document(session_token).set({
            'LineId': line_id,
            'CreatedAt': datetime.now(),
            'ExpiresAt': expires_at,
            'Role': 'User'
        })
        
        logger.info(f"User {line_id} logged in successfully, session: {session_token}")
        
        record_audit_log(
            operator_type="User",
            operator_id=line_id,
            action="LOGIN",
            details={"session_id": session_token[:8] + "..."}
        )
        
        # Redirect to Home with token (or set cookie)
        # Using 303 See Other is better for redirections after logic
        response = RedirectResponse(url=settings.FRONTEND_URL, status_code=303)
        
        # Determine if we should set Secure flag (True if on HTTPS)
        is_secure = settings.FRONTEND_URL.startswith("https")
        
        response.set_cookie(
            key="__session",
            value=session_token,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            path="/",
            max_age=30 * 24 * 60 * 60 # 30 days
        )
        return response

from backend.schemas import UserLogin # Ensure this schema exists or use Body
from fastapi import Body

@router.post('/admin/login')
async def admin_login(username: str = Body(...), password: str = Body(...)):
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        db = get_db()
        sessions_ref = db.collection('Sessions')
        admin_id = 'ADMIN_USER'
        
        # 0. Delete old sessions
        old_sessions = sessions_ref.where('LineId', '==', admin_id).stream()
        for old_s in old_sessions:
            old_s.reference.delete()

        # Create Admin Session
        session_token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=30)
        
        sessions_ref.document(session_token).set({
            'LineId': admin_id,
            'CreatedAt': datetime.now(),
            'ExpiresAt': expires_at,
            'Role': 'Admin'
        })
        
        logger.info(f"Admin logged in successfully, session: {session_token}")
        
        record_audit_log(
            operator_type="Admin",
            operator_id="ADMIN",
            action="LOGIN",
            details={"session_id": session_token[:8] + "..."}
        )
        
        response = RedirectResponse(url='/admin/dashboard.html', status_code=303)
        response.set_cookie(
            key="__session", 
            value=session_token, 
            httponly=True,
            max_age=30 * 24 * 60 * 60 # 30 days
        )
        return response
    else:
        logger.warning(f"Admin login failed for user: {username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get('/logout')
async def logout():
    response = RedirectResponse(url='/')
    response.delete_cookie('__session')
    return response
