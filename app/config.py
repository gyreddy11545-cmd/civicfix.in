import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'civicfix-smart-cities-aurora-innovators-2026-key')
    DATABASE_PATH = os.path.join(BASE_DIR, os.environ.get('DATABASE_PATH', 'civicfix.db'))
    SCHEMA_PATH = os.path.join(BASE_DIR, 'schema.sql')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'heic'}
    
    # Official IC26-04-02 Categories
    CATEGORIES = [
        "Pothole or damaged road",
        "Broken footpath",
        "Streetlight failure",
        "Overflowing garbage bin",
        "Water leakage",
        "Drainage blockage",
        "Damaged public property",
        "Other civic issue"
    ]
    
    SEVERITY_LEVELS = ['Low', 'Medium', 'High', 'Critical']
    
    STATUS_WORKFLOW = [
        'Submitted',
        'Under Review',
        'Verified',
        'Assigned',
        'In Progress',
        'Resolved'
    ]
    
    ALTERNATIVE_STATUSES = ['Rejected', 'Reopened']
    
    # SLA target resolution hours by priority
    SLA_HOURS = {
        'Critical': 24,
        'High': 48,
        'Medium': 72,
        'Low': 120
    }
