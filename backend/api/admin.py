from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from backend.api import deps
from backend.core.database import get_db
import pandas as pd
import io
from datetime import datetime
from backend.schemas import Category, UserUpdate
from backend.core.logger import logger
from backend.core.audit import record_audit_log

router = APIRouter()

# --- Helpers ---
def mask_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return name
    name = name.strip()
    if len(name) == 2:
        return name[0] + "O"
    elif len(name) >= 3:
        return name[0] + "O" * (len(name) - 2) + name[-1]
    return name

# --- Dashboard Stats ---
@router.get("/dashboard")
async def get_admin_dashboard_stats(admin: dict = Depends(deps.get_current_admin)):
    db = get_db()
    
    # 1. Devotion Stats
    devotions = db.collection('Devotions').select(['Amount', 'CategoryName', 'CategoryId']).stream()
    
    total_amount = 0
    count = 0
    cat_dist = {}
    
    for d in devotions:
        data = d.to_dict()
        amt = data.get('Amount', 0)
        cat = data.get('CategoryName') or data.get('CategoryId') or 'Unknown'
        
        total_amount += amt
        count += 1
        cat_dist[cat] = cat_dist.get(cat, 0) + amt
        
    # 2. Pending Approvals count
    pending_count = 0
    pending_users = db.collection('Users').where('IsApproved', '==', False).where('MemberId', '!=', None).stream()
    for _ in pending_users:
        pending_count += 1
        
    logger.debug(f"Admin dashboard loaded: {count} items, {pending_count} pending approvals")
    
    return {
        "total_amount_all": total_amount,
        "total_count": count,
        "category_distribution": cat_dist,
        "pending_approvals_count": pending_count
    }

# --- Upload ---
@router.post("/upload/devotions")
async def upload_devotions(file: UploadFile = File(...), admin: dict = Depends(deps.get_current_admin)):
    # Check extension
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    contents = await file.read()
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents), dtype=str)
            df.Amount = df.Amount.astype(int)
            df.DevotionDate = pd.to_datetime(df.DevotionDate, format='%Y-%m-%d')
        else:
            df = pd.read_excel(io.BytesIO(contents), dtype=str)
            df.Amount = df.Amount.astype(int)
            df.DevotionDate = pd.to_datetime(df.DevotionDate, format='%Y-%m-%d')
    except Exception as e:
         raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
         
    # Expected columns: Date, Category, Amount, MemberId
    required_cols = ['DevotionDate', 'CategoryId','CategoryName','MemberId', 'Amount']
    if not all(col in df.columns for col in required_cols):
        raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required_cols}")
        
    db = get_db()
    batch = db.batch()
    devotions_ref = db.collection('Devotions')
    
    count = 0
    errors = []
    
    for index, row in df.iterrows():
        try:
            # Basic validation
            if pd.isna(row['MemberId']) or pd.isna(row['Amount']):
                raise ValueError("Null values found")
                
            doc_ref = devotions_ref.document() # Auto ID
            
            # Convert Date
            dev_date = row['DevotionDate']
            if not isinstance(dev_date, datetime):
                 dev_date = pd.to_datetime(dev_date)

            data = {
                'MemberId': str(row['MemberId']),
                'CategoryId': str(row['CategoryId']), 
                'CategoryName': str(row['CategoryName']),
                'Amount': int(row['Amount']),
                'DevotionDate': dev_date,
                'CreatedAt': datetime.now()
            }
            batch.set(doc_ref, data)
            count += 1
            
            if count >= 400: # Firestore batch limit is 500
                batch.commit()
                batch = db.batch()
                count = 0
                
        except Exception as e:
            errors.append(f"Row {index+1}: {str(e)}")
            logger.error(f'Error log: {index+1}: {str(e)}')
            
    if count > 0:
        batch.commit()
        
    if errors:
        logger.warning(f"File {file.filename} uploaded with {len(errors)} errors")
        return {"status": "partial_success", "processed": len(df) - len(errors), "errors": errors}
    
    logger.info(f"File {file.filename} uploaded successfully. {len(df)} records processed.")
    
    record_audit_log(
        operator_type="Admin",
        operator_id="ADMIN",
        action="BULK_UPLOAD",
        details={"filename": file.filename, "records": len(df)}
    )
    
    return {"status": "success", "processed": len(df)}

@router.post("/upload/members")
async def upload_members(file: UploadFile = File(...), admin: dict = Depends(deps.get_current_admin)):
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents), dtype = str)
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
         raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
         
    # Expected columns for Members: MemberId, Name
    if 'MemberId' not in df.columns or 'Name' not in df.columns:
        raise HTTPException(status_code=400, detail="Missing columns. Required: ['MemberId', 'Name']")
        
    db = get_db()
    
    # 1. Backup current binding status to preserve it
    current_members = db.collection('Members').stream()
    binding_map = {} # MemberId -> {isBind, BindDate}
    for m in current_members:
        d = m.to_dict()
        if d.get('isBind'):
            binding_map[m.id] = {
                'isBind': True,
                'BindDate': d.get('BindDate')
            }
            
    # 2. Delete all current members (Full Replace)
    docs = db.collection('Members').list_documents()
    batch = db.batch()
    d_count = 0
    for doc in docs:
        batch.delete(doc)
        d_count += 1
        if d_count >= 400:
            batch.commit()
            batch = db.batch()
            d_count = 0
    batch.commit()
    
    # 3. Upload new members
    batch = db.batch()
    count = 0
    for _, row in df.iterrows():
        mid = str(row['MemberId']).strip()
        name = str(row['Name']).strip()
        
        # Apply Masking
        masked_name = mask_name(name)
        
        data = {
            'Name': masked_name,
            'isBind': binding_map.get(mid, {}).get('isBind', False),
            'BindDate': binding_map.get(mid, {}).get('BindDate', None)
        }
        batch.set(db.collection('Members').document(mid), data)
        count += 1
        if count >= 400:
            batch.commit()
            batch = db.batch()
            count = 0
    batch.commit()
    
    logger.info(f"Members full replace completed. {len(df)} records.")
    record_audit_log("Admin", "ADMIN", "UPLOAD_MEMBERS_FULL_REPLACE", details={"records": len(df)})
    
    return {"status": "success", "processed": len(df)}

@router.post("/upload/categories")
async def upload_categories(file: UploadFile = File(...), admin: dict = Depends(deps.get_current_admin)):
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents),dtype = str)
        else:
            df = pd.read_excel(io.BytesIO(contents),dtype = str)
    except Exception as e:
         raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
         
    # Expected columns for Categories: CategoryId, CategoryName, Type
    if 'CategoryId' not in df.columns or 'CategoryName' not in df.columns:
        raise HTTPException(status_code=400, detail="Missing columns. Required: ['CategoryId', 'CategoryName']")
        
    db = get_db()
    
    # 1. Delete all current categories
    docs = db.collection('Categories').list_documents()
    batch = db.batch()
    d_count = 0
    for doc in docs:
        batch.delete(doc)
        d_count += 1
        if d_count >= 400:
            batch.commit()
            batch = db.batch()
            d_count = 0
    batch.commit()
    
    # 2. Upload new categories
    batch = db.batch()
    count = 0
    for _, row in df.iterrows():
        cid = str(row['CategoryId'])
        name = str(row['CategoryName'])
        type_val = str(row['Type']) if 'Type' in df.columns and not pd.isna(row['Type']) else ""
        
        data = {
            'name': name,
            'type': type_val
        }
        batch.set(db.collection('Categories').document(cid), data)
        count += 1
        if count >= 400:
            batch.commit()
            batch = db.batch()
            count = 0
    batch.commit()
    
    logger.info(f"Categories full replace completed. {len(df)} records.")
    record_audit_log("Admin", "ADMIN", "UPLOAD_CATEGORIES_FULL_REPLACE", details={"records": len(df)})
    
    return {"status": "success", "processed": len(df)}

# --- Categories ---
@router.get("/categories")
async def get_categories(admin: dict = Depends(deps.get_current_admin)):
    db = get_db()
    cats = db.collection('Categories').stream()
    return [{"id": c.id, **c.to_dict()} for c in cats]

@router.post("/categories")
async def create_category(cat: Category):
    db = get_db()
    if cat.id:
        # Check if exists to prevent overwrite? Spec doesn't strictly say, but usually good practice.
        # But for 'set', overwriting might be intended or acceptable for admin.
        # Let's check to be safe.
        ref = db.collection('Categories').document(cat.id)
        if ref.get().exists:
             raise HTTPException(status_code=400, detail="Category ID already exists")
    else:
        ref = db.collection('Categories').document()
        
    ref.set(cat.dict())
    
    logger.info(f"Category created: {cat.name} ({ref.id})")
    
    record_audit_log(
        operator_type="Admin",
        operator_id="ADMIN",
        action="CREATE_CATEGORY",
        target_id=ref.id,
        details={"name": cat.name}
    )
    
    return {"status": "created", "id": ref.id}

# --- Users Mgmt ---
@router.delete("/categories/{cat_id}")
async def delete_category(cat_id: str):
    db = get_db()
    # Ideally check usages in Devotions first, but for MVP soft delete or direct delete.
    db.collection('Categories').document(cat_id).delete()
    
    logger.info(f"Category deleted: {cat_id}")
    
    record_audit_log(
        operator_type="Admin",
        operator_id="ADMIN",
        action="DELETE_CATEGORY",
        target_id=cat_id
    )
    
    return {"status": "deleted"}
@router.get("/members")
async def get_members_list(admin: dict = Depends(deps.get_current_admin)):
    db = get_db()
    # List all members from Members collection
    members = db.collection('Members').stream()
    
    # Fetch all Users who have a MemberId (pending or approved)
    users = db.collection('Users').where('MemberId', '!=', None).stream()
    
    # Create mapping: MemberId -> {LineId, LineName, IsApproved, ApplyDate}
    member_user_map = {}
    for u in users:
        ud = u.to_dict()
        mid = ud.get('MemberId')
        if mid:
            member_user_map[mid] = {
                'LineId': u.id,
                'LineName': ud.get('LineName', 'Unknown'),
                'MemberName': ud.get('MemberName', ''), # Provided by user
                'IsApproved': ud.get('IsApproved', False),
                'ApplyDate': ud.get('ApplyDate')
            }

    result = []
    
    for m in members:
        d = m.to_dict()
        d['id'] = m.id 
        
        # Attach User info if there's a record matching this MemberId
        user_info = member_user_map.get(m.id)
        if user_info:
            d['BoundUserName'] = user_info['LineName']
            d['ProvidedName'] = user_info['MemberName'] # Name user typed in
            d['BoundLineId'] = user_info['LineId']
            d['IsApproved'] = user_info['IsApproved']
            d['ApplyDate'] = user_info['ApplyDate']
        else:
            d['IsApproved'] = None # No one applied
            
        result.append(d)
        
    return result

@router.get("/members/{member_id}")
async def get_member_detail(member_id: str):
    db = get_db()
    doc = db.collection('Members').document(member_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Member not found")
        
    data = doc.to_dict()
    data['id'] = doc.id
    
    # If bound, find the User
    if data.get('isBind'):
        users = db.collection('Users').where('MemberId', '==', member_id).limit(1).stream()
        for u in users:
            user_data = u.to_dict()
            data['BoundUser'] = {
                'LineId': u.id,
                'LineName': user_data.get('LineName')
            }
            break
            
    return data

@router.put("/members/{member_id}")
async def update_member(member_id: str, update_data: UserUpdate):
    # Using UserUpdate schema for convenience, though fields might conceptually differ
    db = get_db()
    member_ref = db.collection('Members').document(member_id)
    doc = member_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Member not found")
        
    if update_data.is_unbind:
        # Unbind Logic
        # 1. Update Member
        member_ref.update({'isBind': False})
        
        # 2. Find and update User
        users = db.collection('Users').where('MemberId', '==', member_id).stream()
        for u in users:
            u.reference.update({
                'MemberId': None,
                'MemberName': None,
                'BindDate': None
            })
    else:
        # Update Member details
        updates = {}
        if update_data.member_name:
             updates['Name'] = update_data.member_name
             # Start Sync: Also update MemberName in Devotions? Too expensive for MVP.
             # But should update MemberName in bound Users if any.
        
        if updates:
            member_ref.update(updates)
            
            # Sync to User if bound and Name changed
            if 'Name' in updates and doc.to_dict().get('isBind'):
                 users = db.collection('Users').where('MemberId', '==', member_id).stream()
                 for u in users:
                     u.reference.update({'MemberName': updates['Name']})
    
    logger.info(f"Member {member_id} updated. Unbind={update_data.is_unbind}")
    
    record_audit_log(
        operator_type="Admin",
        operator_id="ADMIN",
        action="UNBIND_MEMBER" if update_data.is_unbind else "UPDATE_MEMBER",
        target_id=member_id,
        details={"is_unbind": update_data.is_unbind, "member_name": update_data.member_name}
    )

    return {"status": "success"}

# --- Binding Approvals ---
@router.post("/members/approve/{line_id}")
async def approve_member_binding(line_id: str, admin: dict = Depends(deps.get_current_admin)):
    db = get_db()
    user_ref = db.collection('Users').document(line_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_data = user_doc.to_dict()
    member_id = user_data.get('MemberId')
    raw_member_name = user_data.get('MemberName', '')
    
    if not member_id:
        raise HTTPException(status_code=400, detail="User has no pending binding")
        
    # Apply Masking on Approval
    masked_name = mask_name(raw_member_name)
    
    # Update User
    now = datetime.now()
    user_ref.update({
        'IsApproved': True,
        'MemberName': masked_name,
        'BindDate': now
    })
    
    # Update Member
    db.collection('Members').document(member_id).update({
        'isBind': True,
        'BindDate': now
    })
    
    logger.info(f"Binding approved for User {line_id} -> Member {member_id}")
    record_audit_log("Admin", "ADMIN", "APPROVE_BINDING", target_id=line_id, details={"member_id": member_id})
    
    return {"status": "success"}

@router.post("/members/reject/{line_id}")
async def reject_member_binding(line_id: str, admin: dict = Depends(deps.get_current_admin)):
    db = get_db()
    user_ref = db.collection('Users').document(line_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_data = user_doc.to_dict()
    member_id = user_data.get('MemberId')
    
    # Clear binding info from User
    user_ref.update({
        'MemberId': None,
        'MemberName': None,
        'IsApproved': False,
        'ApplyDate': None
    })
    
    # Member collection doesn't need update because we didn't set isBind=True yet
    
    logger.info(f"Binding rejected for User {line_id}")
    record_audit_log("Admin", "ADMIN", "REJECT_BINDING", target_id=line_id, details={"member_id": member_id})
    
    return {"status": "success"}

# Additional admin mgmt endpoints here...
@router.get("/audit-logs")
async def get_audit_logs(admin: dict = Depends(deps.get_current_admin)):
    db = get_db()
    logs = db.collection('AuditLogs').order_by('Timestamp', direction='DESCENDING').limit(100).stream()
    return [{"id": l.id, **l.to_dict()} for l in logs]
