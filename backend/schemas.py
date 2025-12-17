from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    role: Optional[str] = None
class UserLogin(BaseModel):
    username: str
    password: str
# --- Models ---

class Category(BaseModel):
    id: Optional[str] = None
    name: str
    type: Optional[str] = None
    note: Optional[str] = None

class Member(BaseModel):
    member_id: str
    member_name: str
    bind_date: Optional[datetime] = None
    is_bind: bool = False

class UserBind(BaseModel):
    member_id: str
    member_name: str
    line_id: str
    line_name: str

class Devotion(BaseModel):
    id: Optional[str] = None
    member_id: str
    member_name: str
    category_id: str
    category_name: Optional[str] = None # Enriched for display
    amount: int
    devotion_date: datetime

class DevotionCreate(BaseModel):
    # Used for individual creation if needed, though mostly bulk upload
    member_id: str
    category_id: str
    amount: int
    devotion_date: datetime

class UserStats(BaseModel):
    member_id: str
    total_amount: int
    total_count: int
    last_devotion_date: Optional[datetime] = None

class DashboardData(BaseModel):
    total_amount: int
    total_count: int
    category_distribution: Dict[str, int] # Category Name -> Amount
    date_distribution: Dict[str, Dict[str, int]] # Date -> {Category -> Amount}
    recent_devotions: List[Devotion]

class AdminDashboardData(BaseModel):
    total_amount_all: int
    category_distribution: Dict[str, int]
    # Add more as needed

class UploadResult(BaseModel):
    success: bool
    total_records: int = 0
    message: str
    errors: Optional[List[str]] = None
