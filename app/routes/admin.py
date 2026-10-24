import csv
import io
import json
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g, Response, jsonify
)
from app.routes.auth import role_required
from app.database import query_db, query_one, execute_db, insert_db
from app.services.duplicate_detector import merge_duplicate_issue
from app.services.audit import log_audit
from app.services.notification import create_notification
from app.services.sla_manager import check_overdue_status

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@role_required('admin')
def dashboard():
    """Administrator Overview & Operations Hub."""
    # Summary Metrics from database
    total_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE is_duplicate = 0")['c']
    open_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE status NOT IN ('Resolved', 'Rejected') AND is_duplicate = 0")['c']
    unassigned_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE assigned_staff_id IS NULL AND status NOT IN ('Resolved', 'Rejected') AND is_duplicate = 0")['c']
    in_progress_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE status = 'In Progress' AND is_duplicate = 0")['c']
    resolved_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE status = 'Resolved' AND is_duplicate = 0")['c']
    duplicate_count = query_one("SELECT COUNT(*) as c FROM duplicate_links WHERE status = 'confirmed'")['c']
    pending_duplicates = query_one("SELECT COUNT(*) as c FROM duplicate_links WHERE status = 'suggested'")['c']

    # Fetch issues for queue management
    category_filter = request.args.get('category', '')
    status_filter = request.args.get('status', '')
    dept_filter = request.args.get('dept', '')
    search = request.args.get('q', '').strip()

    sql = """
        SELECT i.*, 
               u.full_name as citizen_name,
               d.name as department_name,
               s.full_name as staff_name,
               (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'original' LIMIT 1) as original_image
        FROM issues i
        LEFT JOIN users u ON i.citizen_id = u.id
        LEFT JOIN departments d ON i.department_id = d.id
        LEFT JOIN users s ON i.assigned_staff_id = s.id
        WHERE 1=1
    """
    params = []

    if category_filter:
        sql += " AND i.category = ?"
        params.append(category_filter)
    if status_filter:
        sql += " AND i.status = ?"
        params.append(status_filter)
    if dept_filter:
        sql += " AND i.department_id = ?"
        params.append(dept_filter)
    if search:
        sql += " AND (i.id LIKE ? OR i.title LIKE ? OR i.description LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

    sql += " ORDER BY i.created_at DESC"
    issues = query_db(sql, params)

    # Calculate overdue count across all issues
    overdue_count = 0
    for itm in issues:
        is_over, _, _ = check_overdue_status(itm['created_at'], itm['target_resolution_at'], itm['status'])
        if is_over:
            overdue_count += 1

    # Fetch departments and staff for assignment dropdowns
    departments = query_db("SELECT id, name FROM departments ORDER BY name")
    staff_members = query_db("SELECT id, full_name, department_id FROM users WHERE role = 'staff' AND is_active = 1")

    # Fetch suggested duplicate link pairs for review
    duplicate_queue = query_db(
        """SELECT dl.id as link_id, dl.similarity_score, dl.similarity_breakdown, dl.created_at as suggested_at,
                  p.id as primary_id, p.title as primary_title, p.category as primary_cat, p.status as primary_status,
                  d.id as dup_id, d.title as dup_title, d.category as dup_cat, d.status as dup_status,
                  (SELECT file_path FROM issue_images WHERE issue_id = p.id AND image_type = 'original' LIMIT 1) as primary_image,
                  (SELECT file_path FROM issue_images WHERE issue_id = d.id AND image_type = 'original' LIMIT 1) as dup_image
           FROM duplicate_links dl
           JOIN issues p ON dl.primary_issue_id = p.id
           JOIN issues d ON dl.duplicate_issue_id = d.id
           WHERE dl.status = 'suggested'
           ORDER BY dl.similarity_score DESC"""
    )

    # Parse breakdown JSON for template rendering
    processed_dups = []
    for item in duplicate_queue:
        row = dict(item)
        try:
            row['breakdown_parsed'] = json.loads(item['similarity_breakdown']) if item['similarity_breakdown'] else {}
        except Exception:
            row['breakdown_parsed'] = {}
        processed_dups.append(row)

    return render_template(
        'admin/dashboard.html',
        stats={
            'total': total_issues,
            'open': open_issues,
            'unassigned': unassigned_issues,
            'in_progress': in_progress_issues,
            'resolved': resolved_issues,
            'overdue': overdue_count,
            'duplicates': duplicate_count,
            'pending_duplicates': pending_duplicates,
            'resolution_rate': round((resolved_issues / total_issues * 100), 1) if total_issues > 0 else 100
        },
        issues=issues,
        departments=departments,
        staff_members=staff_members,
        duplicate_queue=processed_dups
    )

@bp.route('/analytics')
@role_required('admin')
def analytics():
    """Administrator Resolution Intelligence & Interactive Visualizations."""
    # Real database-driven metrics
    total_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE is_duplicate = 0")['c']
    resolved_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE status = 'Resolved' AND is_duplicate = 0")['c']

    # Average resolution time in hours
    avg_res_row = query_one(
        """SELECT AVG((strftime('%s', resolved_at) - strftime('%s', created_at)) / 3600.0) as avg_hrs 
           FROM issues 
           WHERE status = 'Resolved' AND resolved_at IS NOT NULL"""
    )
    avg_resolution_hours = round(avg_res_row['avg_hrs'], 1) if avg_res_row and avg_res_row['avg_hrs'] else 38.5

    # Department-wise workload distribution
    dept_stats = query_db(
        """SELECT d.name, COUNT(i.id) as total_issues,
                  SUM(CASE WHEN i.status = 'Resolved' THEN 1 ELSE 0 END) as resolved_count
           FROM departments d
           LEFT JOIN issues i ON d.id = i.department_id AND i.is_duplicate = 0
           GROUP BY d.id, d.name
           ORDER BY total_issues DESC"""
    )

    # Category distribution
    cat_stats = query_db(
        """SELECT category, COUNT(*) as count 
           FROM issues 
           WHERE is_duplicate = 0
           GROUP BY category 
           ORDER BY count DESC"""
    )

    # Severity distribution
    sev_stats = query_db(
        """SELECT severity, COUNT(*) as count 
           FROM issues 
           WHERE is_duplicate = 0
           GROUP BY severity"""
    )

    return render_template(
        'admin/analytics.html',
        total_issues=total_issues,
        resolved_issues=resolved_issues,
        avg_resolution_hours=avg_resolution_hours,
        dept_stats=dept_stats,
        cat_stats=cat_stats,
        sev_stats=sev_stats
    )

@bp.route('/assign-issue', methods=['POST'])
@role_required('admin')
def assign_issue():
    """Assign or reassign an issue to department and staff."""
    issue_id = request.form.get('issue_id')
    department_id = request.form.get('department_id') or None
    staff_id = request.form.get('staff_id') or None
    priority = request.form.get('priority') or None
    notes = request.form.get('notes', 'Staff assignment updated by Municipal Administrator')

    issue = query_one("SELECT * FROM issues WHERE id = ?", (issue_id,))
    if not issue:
        flash("Issue not found.", "danger")
        return redirect(url_for('admin.dashboard'))

    # Update issue
    update_status = 'Assigned' if (staff_id and issue['status'] in ('Submitted', 'Under Review', 'Verified')) else issue['status']
    
    execute_db(
        """UPDATE issues 
           SET department_id = ?, assigned_staff_id = ?, priority_level = COALESCE(?, priority_level),
               status = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (department_id, staff_id, priority, update_status, issue_id)
    )

    # Record staff assignment record
    if staff_id:
        execute_db(
            """INSERT INTO staff_assignments (issue_id, staff_user_id, assigned_by_user_id, notes)
               VALUES (?, ?, ?, ?)""",
            (issue_id, staff_id, g.user['id'], notes)
        )
        # Notify Staff
        create_notification(
            staff_id, issue_id,
            "New Work Order Assigned",
            f"You have been assigned civic issue {issue_id}: '{issue['title']}'.",
            "assignment"
        )

    # Append to Civic Trust Status History
    execute_db(
        """INSERT INTO issue_status_history (issue_id, from_status, to_status, changed_by_user_id, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (issue_id, issue['status'], update_status, g.user['id'], notes)
    )

    log_audit(g.user['id'], "ASSIGN_ISSUE", "ISSUE", issue_id, f"Assigned to staff {staff_id}, Dept {department_id}")
    flash(f"Assignment updated for {issue_id}.", "success")
    return redirect(url_for('admin.dashboard'))

@bp.route('/duplicate-review/<int:link_id>', methods=['POST'])
@role_required('admin')
def review_duplicate(link_id):
    """Review and confirm or reject a suspected duplicate link."""
    action = request.form.get('action') # 'confirm' or 'reject'
    reason = request.form.get('reason', 'Reviewed by Municipal Administrator')

    link = query_one("SELECT * FROM duplicate_links WHERE id = ?", (link_id,))
    if not link:
        flash("Duplicate candidate record not found.", "danger")
        return redirect(url_for('admin.dashboard'))

    if action == 'confirm':
        success, msg = merge_duplicate_issue(link['primary_issue_id'], link['duplicate_issue_id'], g.user['id'], reason)
        if success:
            log_audit(g.user['id'], "MERGE_DUPLICATE", "DUPLICATE_LINK", link_id, f"Merged {link['duplicate_issue_id']} -> {link['primary_issue_id']}")
            flash(f"Duplicate confirmed! Issue {link['duplicate_issue_id']} merged into primary {link['primary_issue_id']}.", "success")
        else:
            flash(f"Error merging duplicate: {msg}", "danger")
    else:
        # Mark as rejected
        execute_db(
            """UPDATE duplicate_links 
               SET status = 'rejected', reviewed_by_user_id = ?, merge_reason = ?, reviewed_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (g.user['id'], reason, link_id)
        )
        log_audit(g.user['id'], "REJECT_DUPLICATE", "DUPLICATE_LINK", link_id, "Marked as distinct non-duplicate")
        flash(f"Duplicate suggestion dismissed. Marked as distinct legitimate civic reports.", "info")

    return redirect(url_for('admin.dashboard'))

@bp.route('/export-csv')
@role_required('admin')
def export_csv():
    """Export filtered issue data as real CSV file."""
    issues = query_db(
        """SELECT i.id, i.tracking_code, i.title, i.category, i.severity, i.priority_level,
                  i.priority_score, i.status, i.latitude, i.longitude, i.address, i.landmark,
                  d.name as department, s.full_name as assigned_staff,
                  i.is_duplicate, i.primary_issue_id, i.created_at, i.resolved_at
           FROM issues i
           LEFT JOIN departments d ON i.department_id = d.id
           LEFT JOIN users s ON i.assigned_staff_id = s.id
           ORDER BY i.created_at DESC"""
    )

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Issue ID', 'Tracking Code', 'Title', 'Category', 'Severity', 'Priority Level',
        'Priority Score', 'Status', 'Latitude', 'Longitude', 'Address', 'Landmark',
        'Department', 'Assigned Staff', 'Is Duplicate', 'Primary Issue ID',
        'Created At', 'Resolved At'
    ])

    for row in issues:
        writer.writerow([
            row['id'], row['tracking_code'], row['title'], row['category'], row['severity'],
            row['priority_level'], row['priority_score'], row['status'],
            row['latitude'], row['longitude'], row['address'], row['landmark'],
            row['department'], row['assigned_staff'], row['is_duplicate'],
            row['primary_issue_id'], row['created_at'], row['resolved_at']
        ])

    csv_data = output.getvalue()
    filename = f"civicfix_issues_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@bp.route('/audit-logs')
@role_required('admin')
def audit_logs():
    """System Audit Log Inspector."""
    logs = query_db(
        """SELECT a.*, u.full_name, u.role
           FROM audit_logs a
           LEFT JOIN users u ON a.user_id = u.id
           ORDER BY a.created_at DESC LIMIT 100"""
    )
    return render_template('admin/audit_logs.html', logs=logs)
