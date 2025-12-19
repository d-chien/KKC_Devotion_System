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

# --- Dashboard Stats ---
@router.get("/dashboard")
async def get_admin_dashboard_stats():
    db = get_db()
    
    # 1. Get Total Count using Aggregation Query (Efficient)
    # Note: aggregation_query is available in newer google-cloud-firestore
    # If not available in current env, fallback to count loop, but let's try standard way.
    # Actually, standard python client supports collection_group query count, or collection count.
    
    # Simple count query
    # collection_ref = db.collection('Devotions')
    # count_query = collection_ref.count()
    # count_snapshot = count_query.get()
    # total_count = count_snapshot[0][0].value 
    
    # However, 'count()' is in newer library versions. Let's stick to safe optimization: Projection.
    # We only need Amount and Category for stats.
    
    devotions = db.collection('Devotions').select(['Amount', 'CategoryName', 'CategoryId']).stream()
    
    total_amount = 0
    count = 0
    cat_dist = {}
    
    for d in devotions:
        # data is partial dict due to select
        data = d.to_dict()
        amt = data.get('Amount', 0)
        # Use CategoryName preferred, fallback to ID
        cat = data.get('CategoryName') or data.get('CategoryId') or 'Unknown'
        
        total_amount += amt
        count += 1
        cat_dist[cat] = cat_dist.get(cat, 0) + amt
        
    logger.debug(f"Admin dashboard loaded: {count} items, total {total_amount}")
    
    return {
        "total_amount_all": total_amount,
        "total_count": count,
        "category_distribution": cat_dist
    }

# --- Upload ---
@router.post("/upload")
async def upload_devotions(file: UploadFile = File(...)):
    # Check extension
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    contents = await file.read()
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
         raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
         
    # Expected columns: Date, Category, Amount, MemberId, MemberName
    required_cols = ['Date', 'Category', 'Amount', 'MemberId']
    if not all(col in df.columns for col in required_cols):
        raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required_cols}")
        
    db = get_db()
    batch = db.batch()
    devotions_ref = db.collection('Devotions')
    
    count = 0
    errors = []
    
    # Pre-fetch categories map to ID? Or just store Name?
    # Spec says "Category Id", "Category Name".
    
    for index, row in df.iterrows():
        try:
            # Basic validation
            if pd.isna(row['MemberId']) or pd.isna(row['Amount']):
                raise ValueError("Null values found")
                
            doc_ref = devotions_ref.document() # Auto ID
            
            # Convert Date
            dev_date = row['Date']
            if not isinstance(dev_date, datetime):
                 dev_date = pd.to_datetime(dev_date)

            data = {
                'MemberId': str(row['MemberId']),
                'MemberName': row.get('MemberName', ''),
                'CategoryId': str(row['Category']), # Using Name as ID for simplicity or lookup
                'CategoryName': str(row['Category']),
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

# --- Categories ---
@router.get("/categories")
async def get_categories():
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
async def get_members_list():
    db = get_db()
    # List all members from Members collection
    members = db.collection('Members').stream()
    
    # Optimize: Fetch all Users who are bound to map MemberId -> LineName
    # This avoids N+1 queries.
    users = db.collection('Users').where('MemberId', '!=', None).stream()
    
    # Create mapping: MemberId -> LineName
    member_user_map = {}
    for u in users:
        ud = u.to_dict()
        mid = ud.get('MemberId')
        if mid:
            member_user_map[mid] = ud.get('LineName', 'Unknown')

    result = []
    
    for m in members:
        d = m.to_dict()
        d['id'] = m.id 
        
        # Attach BoundUserName if bound
        if d.get('isBind'):
            d['BoundUserName'] = member_user_map.get(m.id)
            
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

# Additional admin mgmt endpoints here...
@router.get("/audit-logs")
async def get_audit_logs():
    db = get_db()
    logs = db.collection('AuditLogs').order_by('Timestamp', direction='DESCENDING').limit(100).stream()
    return [{"id": l.id, **l.to_dict()} for l in logs]
