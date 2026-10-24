from datetime import datetime, timedelta

# Target resolution hours by priority
DEFAULT_SLA_HOURS = {
    'Critical': 24,
    'High': 48,
    'Medium': 72,
    'Low': 120
}

def calculate_target_resolution(created_at, priority_level):
    """Calculate the target resolution timestamp based on priority SLA."""
    if isinstance(created_at, str):
        try:
            created_at = datetime.strptime(created_at.split('.')[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            created_at = datetime.utcnow()
    hours = DEFAULT_SLA_HOURS.get(priority_level, 72)
    return created_at + timedelta(hours=hours)

def check_overdue_status(created_at, target_resolution_at, status):
    """
    Check if an issue is overdue.
    Returns: (is_overdue, hours_overdue_or_remaining, status_badge_text)
    """
    if status in ('Resolved', 'Rejected'):
        return False, 0, "Completed"
        
    if not target_resolution_at:
        return False, 0, "No SLA Set"
        
    if isinstance(target_resolution_at, str):
        try:
            target_resolution_at = datetime.strptime(target_resolution_at.split('.')[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            return False, 0, "Active"
            
    now = datetime.utcnow()
    diff = now - target_resolution_at
    
    if diff.total_seconds() > 0:
        # Overdue
        hours = int(diff.total_seconds() // 3600)
        days = hours // 24
        if days > 0:
            badge = f"Overdue by {days}d {hours % 24}h"
        else:
            badge = f"Overdue by {hours}h"
        return True, hours, badge
    else:
        # Remaining
        rem_hours = int(abs(diff.total_seconds()) // 3600)
        days = rem_hours // 24
        if days > 0:
            badge = f"{days}d {rem_hours % 24}h remaining"
        else:
            badge = f"{rem_hours}h remaining"
        return False, rem_hours, badge
