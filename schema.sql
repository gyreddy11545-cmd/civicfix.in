-- CivicFix Database Schema (SQLite compatible, prepared for MySQL migration)

PRAGMA foreign_keys = ON;

-- 1. Departments Table
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    contact_email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    role TEXT NOT NULL CHECK(role IN ('citizen', 'staff', 'admin')),
    department_id INTEGER,
    avatar_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

-- 3. Issues Table
CREATE TABLE IF NOT EXISTS issues (
    id TEXT PRIMARY KEY, -- e.g. CF-2026-0001
    tracking_code TEXT NOT NULL UNIQUE,
    citizen_id INTEGER,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('Low', 'Medium', 'High', 'Critical')),
    priority_level TEXT NOT NULL DEFAULT 'Medium', -- Low, Medium, High, Critical
    priority_score INTEGER DEFAULT 50, -- 0 to 100
    priority_reason TEXT,
    status TEXT NOT NULL DEFAULT 'Submitted' CHECK(status IN ('Submitted', 'Under Review', 'Verified', 'Assigned', 'In Progress', 'Resolved', 'Rejected', 'Reopened')),
    latitude REAL,
    longitude REAL,
    address TEXT,
    landmark TEXT,
    department_id INTEGER,
    assigned_staff_id INTEGER,
    target_resolution_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    resolution_staff_id INTEGER,
    is_duplicate INTEGER DEFAULT 0,
    primary_issue_id TEXT,
    reopen_reason TEXT,
    rejection_reason TEXT,
    is_demo INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (citizen_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_staff_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (resolution_staff_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (primary_issue_id) REFERENCES issues(id) ON DELETE SET NULL
);

-- 4. Issue Images Table (Original, Resolution, and Progress Evidence)
CREATE TABLE IF NOT EXISTS issue_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id TEXT NOT NULL,
    image_type TEXT NOT NULL CHECK(image_type IN ('original', 'resolution', 'progress')),
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    caption TEXT,
    uploaded_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 5. Issue Status History (Civic Trust Audit Trail)
CREATE TABLE IF NOT EXISTS issue_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    changed_by_user_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 6. Staff Assignments Table
CREATE TABLE IF NOT EXISTS staff_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id TEXT NOT NULL,
    staff_user_id INTEGER NOT NULL,
    assigned_by_user_id INTEGER,
    notes TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (staff_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 7. Duplicate Links Table (Transparent duplicate detection & merging)
CREATE TABLE IF NOT EXISTS duplicate_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    primary_issue_id TEXT NOT NULL,
    duplicate_issue_id TEXT NOT NULL UNIQUE,
    similarity_score INTEGER NOT NULL, -- 0-100
    similarity_breakdown TEXT, -- JSON breakdown of category, geo, text, time
    status TEXT NOT NULL DEFAULT 'suggested' CHECK(status IN ('suggested', 'confirmed', 'rejected')),
    reviewed_by_user_id INTEGER,
    merge_reason TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (primary_issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (duplicate_issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 8. Issue Comments & Progress Notes
CREATE TABLE IF NOT EXISTS issue_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id TEXT NOT NULL,
    user_id INTEGER,
    comment_text TEXT NOT NULL,
    is_internal INTEGER DEFAULT 0, -- 0 = public citizen-facing, 1 = internal staff note
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 9. Citizen Feedback & Confirmations
CREATE TABLE IF NOT EXISTS citizen_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id TEXT NOT NULL,
    citizen_id INTEGER NOT NULL,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    confirmed_resolved INTEGER DEFAULT 1, -- 1 = confirmed fixed, 0 = disputed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (citizen_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 10. Community Confirmations (Prevent duplicate votes per user)
CREATE TABLE IF NOT EXISTS community_confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    confirmed_fixed INTEGER DEFAULT 1, -- 1 = agrees fixed, 0 = disagrees
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(issue_id, user_id),
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 11. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    issue_id TEXT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT DEFAULT 'status_update',
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE SET NULL
);

-- 12. Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for high-performance querying
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_category ON issues(category);
CREATE INDEX IF NOT EXISTS idx_issues_citizen ON issues(citizen_id);
CREATE INDEX IF NOT EXISTS idx_issues_assigned ON issues(assigned_staff_id);
CREATE INDEX IF NOT EXISTS idx_issues_department ON issues(department_id);
CREATE INDEX IF NOT EXISTS idx_issues_geo ON issues(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_issues_created ON issues(created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
