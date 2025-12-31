from fastapi import APIRouter, Depends, HTTPException
from backend.api import deps
from backend.schemas import DashboardData, Devotion, UserBind
from backend.core.database import get_db
from backend.core.logger import logger
from backend.core.audit import record_audit_log
from typing import List, Optional
from datetime import datetime

router = APIRouter()

@router.get('/me')
async def get_me(current_user: dict = Depends(deps.get_current_user)):
    logger.debug(f"Fetching profile for user: {current_user.get('LineId')}")
    return {
        "LineId": current_user.get('LineId'),
        "LineName": current_user.get('LineName'),
        "MemberId": current_user.get('MemberId'),
        "IsBound": bool(current_user.get('MemberId') and current_user.get('IsApproved')),
        "IsApproved": current_user.get('IsApproved', False),
        "ApplyDate": current_user.get('ApplyDate')
    }

@router.post('/bind')
async def bind_user(bind_data: UserBind, current_user: dict = Depends(deps.get_current_user)):
    db = get_db()
    
    # 1. Check if user already bound or pending
    if current_user.get('MemberId') and current_user.get('IsApproved'):
        raise HTTPException(status_code=400, detail="User already bound")
    
    # 2. Check if MemberId exists in Members collection
    members_ref = db.collection('Members')
    member_doc = members_ref.document(bind_data.member_id).get()
    
    if not member_doc.exists:
        raise HTTPException(status_code=400, detail="Member ID not found")
    
    member_info = member_doc.to_dict()
    
    if member_info.get('isBind'):
         raise HTTPException(status_code=400, detail="Member ID already bound by another user")
         
    # 3. Update User with application info
    users_ref = db.collection('Users')
    users_ref.document(current_user['LineId']).update({
        'MemberId': bind_data.member_id,
        'MemberName': member_info.get('Name'), # Store the masked name from Members
        'IsApproved': False,
        'ApplyDate': datetime.now()
    })
    
    # We DON'T update Members.isBind here, only after approval.
    
    logger.info(f"User {current_user['LineId'][:10]} applied for Member {bind_data.member_id}")
    
    record_audit_log(
        operator_type="User",
        operator_id=current_user['LineId'],
        action="APPLY_BIND",
        target_id=bind_data.member_id,
        details={"member_name": member_info.get('Name')}
    )
    
    return {"status": "pending", "message": "綁定申請中"}

@router.get('/dashboard')
async def get_dashboard(current_user: dict = Depends(deps.get_current_user)):
    member_id = current_user.get('MemberId')
    is_approved = current_user.get('IsApproved', False)
    if not member_id or not is_approved:
        raise HTTPException(status_code=403, detail="User not bound or not yet approved")
        
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
    
    logger.debug(f"Dashboard loaded for user {member_id}: {len(devotions)} items")
    
    return {
        "total_amount": total_amount,
        "total_count": len(devotions),
        "category_distribution": cat_dist,
        "recent_devotions": devotions
    }
