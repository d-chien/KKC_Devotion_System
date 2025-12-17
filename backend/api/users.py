from fastapi import APIRouter, Depends, HTTPException
from backend.api import deps
from backend.schemas import DashboardData, Devotion, UserBind
from backend.core.database import get_db
from typing import List, Optional
from datetime import datetime

router = APIRouter()

@router.get('/me')
async def get_me(current_user: dict = Depends(deps.get_current_user)):
    return {
        "LineId": current_user.get('LineId'),
        "LineName": current_user.get('LineName'),
        "MemberId": current_user.get('MemberId'),
        "MemberName": current_user.get('MemberName'),
        "IsBound": bool(current_user.get('MemberId'))
    }

@router.post('/bind')
async def bind_user(bind_data: UserBind, current_user: dict = Depends(deps.get_current_user)):
    db = get_db()
    # Check if MemberId is valid in Members collection
    members_ref = db.collection('Members')
    member_doc = members_ref.document(bind_data.member_id).get()
    
    if not member_doc.exists:
        raise HTTPException(status_code=400, detail="Member ID not found")
    
    member_info = member_doc.to_dict()
    # Optional: Check name matches or something
    
    if member_info.get('isBind'):
         raise HTTPException(status_code=400, detail="Member ID already bound")
         
    # Update User
    users_ref = db.collection('Users')
    users_ref.document(current_user['LineId']).update({
        'MemberId': bind_data.member_id,
        'MemberName': bind_data.member_name, # or use name from DB
        'BindDate': datetime.now()
    })
    
    # Update Member
    members_ref.document(bind_data.member_id).update({
        'isBind': True
    })
    
    return {"status": "success"}

@router.get('/dashboard')
async def get_dashboard(current_user: dict = Depends(deps.get_current_user)):
    member_id = current_user.get('MemberId')
    if not member_id:
        raise HTTPException(status_code=403, detail="User not bound")
        
    db = get_db()
    
    # Fetch devotions
    devotions_ref = db.collection('Devotions')
    query = devotions_ref.where('MemberId', '==', member_id)
    # Note: Firestore might need composite index for sorting by date
    docs = query.stream()
    
    devotions = []
    total_amount = 0
    cat_dist = {}
    
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        devotions.append(d)
        
        amt = d.get('Amount', 0)
        total_amount += amt
        
        # Category aggregation
        cat_id = d.get('CategoryId')
        # We might want Category Name here, assumed stored or lookup
        cat_name = d.get('CategoryName', cat_id) 
        cat_dist[cat_name] = cat_dist.get(cat_name, 0) + amt

    # Sort in memory for now (MVP)
    devotions.sort(key=lambda x: x.get('DevotionDate', ''), reverse=True)
    
    return {
        "total_amount": total_amount,
        "total_count": len(devotions),
        "category_distribution": cat_dist,
        "recent_devotions": devotions
    }
