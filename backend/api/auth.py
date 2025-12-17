from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
import httpx
import uuid
from datetime import datetime
from backend.core.config import settings
from backend.core.database import get_db
from backend.schemas import Token
from backend.api import deps
# Only import if you have deps specific logic, otherwise define here

router = APIRouter()

# LINE API URLs
LINE_AUTH_URL = 'https://access.line.me/oauth2/v2.1/authorize'
LINE_TOKEN_URL = 'https://api.line.me/oauth2/v2.1/token'
LINE_PROFILE_URL = 'https://api.line.me/v2/profile'

@router.get('/line/login')
async def line_login(request: Request):
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
        raise HTTPException(status_code=400, detail=error_description)
    
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
            
        # Create Session
        session_token = str(uuid.uuid4())
        # Store session in Firestore
        sessions_ref = db.collection('Sessions')
        sessions_ref.document(session_token).set({
            'LineId': line_id,
            'CreatedAt': datetime.now(),
            'Role': 'User'
        })
        
        # Redirect to Home with token (or set cookie)
        response = RedirectResponse(url='/') # Frontend handle
        response.set_cookie(key="__session", value=session_token, httponly=True)
        return response

@router.post('/admin/login')
async def admin_login():
    # Placeholder for admin login
    # In real world, check username/password against DB
    return {"message": "Admin Login Endpoint"}

@router.get('/logout')
async def logout():
    response = RedirectResponse(url='/')
    response.delete_cookie('__session')
    return response
