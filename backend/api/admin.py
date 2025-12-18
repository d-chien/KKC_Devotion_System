from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from backend.api import deps
from backend.core.database import get_db
import pandas as pd
import io
from datetime import datetime
from backend.schemas import Category

router = APIRouter()

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
        return {"status": "partial_success", "processed": len(df) - len(errors), "errors": errors}
        
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
    ref = db.collection('Categories').document()
    ref.set(cat.dict())
    return {"status": "created", "id": ref.id}

# --- Users Mgmt ---
@router.get("/users")
async def get_users_list():
    db = get_db()
    users = db.collection('Users').stream()
    return [{"LineId": u.id, **u.to_dict()} for u in users]

@router.get("/users/{user_id}")
async def get_user_detail(user_id: str):
    db = get_db()
    doc = db.collection('Users').document(user_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    return {"LineId": doc.id, **doc.to_dict()}

from backend.schemas import UserUpdate
@router.put("/users/{user_id}")
async def update_user(user_id: str, update_data: UserUpdate):
    db = get_db()
    user_ref = db.collection('Users').document(user_id)
    doc = user_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
        
    current_data = doc.to_dict()
    
    updates = {}
    if update_data.is_unbind:
        # Unbind
        updates = {
            'MemberId': None,
            'MemberName': None,
            'BindDate': None
        }
        # Also update Members collection to release binding
        old_member_id = current_data.get('MemberId')
        if old_member_id:
             db.collection('Members').document(old_member_id).update({'isBind': False})
             
    else:
        # Update info (re-bind or fix name)
        if update_data.member_id is not None:
             updates['MemberId'] = update_data.member_id
        if update_data.member_name is not None:
             updates['MemberName'] = update_data.member_name
             
        # Note: If changing MemberId, need to handle old member isBind status and new member isBind status.
        # This is strictly admin override, so we assume admin knows what they are doing,
        # but logic should ideally check if new member is already bound.
        
    if updates:
        user_ref.update(updates)
        
    return {"status": "success", "updated": updates}

# Additional admin mgmt endpoints here...
