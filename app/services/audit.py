from flask import request
from app.database import execute_db

def log_audit(user_id, action, entity_type, entity_id, details=""):
    """Record an action in the system audit log."""
    try:
        ip = request.remote_addr if request else "127.0.0.1"
    except Exception:
        ip = "127.0.0.1"
        
    try:
        execute_db(
            """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, action, entity_type, str(entity_id), str(details), ip)
        )
    except Exception as e:
        print(f"Error logging audit: {e}")
