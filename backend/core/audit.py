from datetime import datetime
from typing import Any, Dict, Optional
from backend.core.database import get_db
from backend.core.logger import logger

def record_audit_log(
    operator_type: str,
    operator_id: str,
    action: str,
    target_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    try:
        db = get_db()
        audit_ref = db.collection('AuditLogs')
        
        log_entry = {
            "OperatorType": operator_type,
            "OperatorId": operator_id,
            "Action": action,
            "TargetId": target_id,
            "Details": details or {},
            "Timestamp": datetime.now()
        }
        
        audit_ref.add(log_entry)
        logger.info(f"Audit log recorded: {action} by {operator_type} {operator_id}")
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
