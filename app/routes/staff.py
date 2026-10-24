import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g, current_app, jsonify
)
from app.routes.auth import login_required, role_required
from app.database import query_db, query_one, execute_db, insert_db
from app.services.sla_manager import check_overdue_status
from app.services.audit import log_audit
from app.services.notification import create_notification

bp = Blueprint('staff', __name__, url_prefix='/staff')

@bp.route('/dashboard')
@role_required('staff', 'admin')
def dashboard():
    staff_id = g.user['id']
    dept_id = g.user['department_id']

    # Filter parameters
    view_tab = request.args.get('tab', 'assigned') # 'assigned', 'department', 'all'
    status_filter = request.args.get('status', '')
    severity_filter = request.args.get('severity', '')
    overdue_only = request.args.get('overdue', '0') == '1'

    # Build SQL based on tab
    base_sql = """
        SELECT i.*, 
               u.full_name as citizen_name, u.phone as citizen_phone,
               d.name as department_name,
               s.full_name as staff_name,
               (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'original' LIMIT 1) as original_image,
               (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'resolution' LIMIT 1) as resolution_image
        FROM issues i
        LEFT JOIN users u ON i.citizen_id = u.id
        LEFT JOIN departments d ON i.department_id = d.id
        LEFT JOIN users s ON i.assigned_staff_id = s.id
        WHERE i.is_duplicate = 0
    """
    params = []

    if view_tab == 'assigned':
        base_sql += " AND i.assigned_staff_id = ?"
        params.append(staff_id)
    elif view_tab == 'department' and dept_id:
        base_sql += " AND (i.department_id = ? OR i.assigned_staff_id = ?)"
        params.extend([dept_id, staff_id])

    if status_filter:
        base_sql += " AND i.status = ?"
        params.append(status_filter)
    if severity_filter:
        base_sql += " AND i.severity = ?"
        params.append(severity_filter)

    base_sql += " ORDER BY i.created_at DESC"
    raw_issues = query_db(base_sql, params)

    # Process SLA and overdue indicators
    processed_issues = []
    overdue_count = 0
    assigned_count = 0
    in_progress_count = 0
    resolved_count = 0

    for issue in raw_issues:
        is_overdue, hours, sla_badge = check_overdue_status(
            issue['created_at'], issue['target_resolution_at'], issue['status']
        )
        issue_dict = dict(issue)
        issue_dict['is_overdue'] = is_overdue
        issue_dict['sla_badge'] = sla_badge

        if is_overdue:
            overdue_count += 1
        if issue['assigned_staff_id'] == staff_id:
            assigned_count += 1
        if issue['status'] == 'In Progress':
            in_progress_count += 1
        elif issue['status'] == 'Resolved':
            resolved_count += 1

        if overdue_only and not is_overdue:
            continue
        processed_issues.append(issue_dict)

    # All departments list for assignment dropdowns
    departments = query_db("SELECT id, name FROM departments ORDER BY name")

    return render_template(
        'staff/dashboard.html',
        issues=processed_issues,
        departments=departments,
        view_tab=view_tab,
        stats={
            'assigned': assigned_count,
            'in_progress': in_progress_count,
            'resolved': resolved_count,
            'overdue': overdue_count
        }
    )

@bp.route('/issues/<issue_id>/update-status', methods=['POST'])
@role_required('staff', 'admin')
def update_status(issue_id):
    """
    Controlled status progression:
    Submitted -> Under Review -> Verified -> Assigned -> In Progress -> Resolved
    Plus Reopened and Rejected states.
    """
    new_status = request.form.get('status', '').strip()
    notes = request.form.get('notes', '').strip()
    staff_id = g.user['id']

    issue = query_one("SELECT * FROM issues WHERE id = ?", (issue_id,))
    if not issue:
        flash("Issue not found.", "danger")
        return redirect(url_for('staff.dashboard'))

    old_status = issue['status']

    # Validation: Rejection requires mandatory reason
    if new_status == 'Rejected':
        rejection_reason = request.form.get('rejection_reason', '').strip() or notes
        if not rejection_reason:
            flash("Rejection requires a mandatory explanation.", "warning")
            return redirect(url_for('public.issue_detail', issue_id=issue_id))
        execute_db(
            """UPDATE issues 
               SET status = 'Rejected', rejection_reason = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (rejection_reason, issue_id)
        )
        notes = f"Rejected: {rejection_reason}"
    else:
        execute_db(
            """UPDATE issues 
               SET status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (new_status, issue_id)
        )

    # Append to Civic Trust Status History
    execute_db(
        """INSERT INTO issue_status_history (issue_id, from_status, to_status, changed_by_user_id, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (issue_id, old_status, new_status, staff_id, notes or f"Status updated to {new_status} by municipal staff")
    )

    # Notify Citizen
    if issue['citizen_id']:
        create_notification(
            issue['citizen_id'], issue_id,
            f"Issue Status Updated: {new_status}",
            f"Your report {issue_id} status has been updated from '{old_status}' to '{new_status}'.",
            "status_update"
        )

    log_audit(staff_id, "UPDATE_STATUS", "ISSUE", issue_id, f"Changed status from {old_status} to {new_status}")
    flash(f"Status for {issue_id} successfully changed to '{new_status}'.", "success")
    return redirect(url_for('public.issue_detail', issue_id=issue_id))

@bp.route('/issues/<issue_id>/resolve', methods=['POST'])
@role_required('staff', 'admin')
def resolve_issue(issue_id):
    """
    Resolution Form Submission with After-Repair Photograph.
    Requires resolution description, resolution photo upload, and updates database.
    """
    description = request.form.get('resolution_description', '').strip()
    staff_id = g.user['id']

    if not description:
        flash("Resolution description is mandatory.", "warning")
        return redirect(url_for('public.issue_detail', issue_id=issue_id))

    # Handle resolution photo
    file = request.files.get('resolution_photo')
    file_path = None
    orig_filename = None
    file_size = 0

    if file and file.filename != '':
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']):
            flash("Invalid photo format. Please upload JPG, PNG, or WEBP.", "danger")
            return redirect(url_for('public.issue_detail', issue_id=issue_id))

        orig_filename = secure_filename(file.filename)
        unique_name = f"res_{int(datetime.utcnow().timestamp())}_{orig_filename}"
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'resolutions', unique_name)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        file.save(save_path)
        file_size = os.path.getsize(save_path)
        file_path = f"/static/uploads/resolutions/{unique_name}"

    now = datetime.utcnow()
    # Update issue record
    execute_db(
        """UPDATE issues 
           SET status = 'Resolved', resolved_at = ?, resolution_notes = ?, resolution_staff_id = ?, updated_at = ?
           WHERE id = ?""",
        (now, description, staff_id, now, issue_id)
    )

    # Save resolution image if provided
    if file_path:
        execute_db(
            """INSERT INTO issue_images (issue_id, image_type, file_path, file_name, file_size, caption, uploaded_by_user_id)
               VALUES (?, 'resolution', ?, ?, ?, 'Resolution proof: After-repair evidence', ?)""",
            (issue_id, file_path, orig_filename, file_size, staff_id)
        )

    # Append to Civic Trust Status History
    execute_db(
        """INSERT INTO issue_status_history (issue_id, from_status, to_status, changed_by_user_id, notes)
           VALUES (?, 'In Progress', 'Resolved', ?, ?)""",
        (issue_id, staff_id, f"Resolved with repair evidence: {description}")
    )

    # Notify Citizen
    issue = query_one("SELECT citizen_id FROM issues WHERE id = ?", (issue_id,))
    if issue and issue['citizen_id']:
        create_notification(
            issue['citizen_id'], issue_id,
            "Issue Successfully Resolved!",
            f"Municipal staff have completed repairs on report {issue_id}. Please review resolution proof and confirm completion.",
            "resolved"
        )

    log_audit(staff_id, "RESOLVE_ISSUE", "ISSUE", issue_id, f"Resolved issue with evidence photo: {description}")
    flash(f"Issue {issue_id} has been marked as Resolved with evidence.", "success")
    return redirect(url_for('public.issue_detail', issue_id=issue_id))

@bp.route('/issues/<issue_id>/add-note', methods=['POST'])
@role_required('staff', 'admin')
def add_progress_note(issue_id):
    """Add progress note (can be internal staff only or public to citizen)."""
    note_text = request.form.get('note_text', '').strip()
    is_internal = int(request.form.get('is_internal', 0))
    staff_id = g.user['id']

    if not note_text:
        flash("Note text cannot be empty.", "warning")
        return redirect(url_for('public.issue_detail', issue_id=issue_id))

    insert_db(
        """INSERT INTO issue_comments (issue_id, user_id, comment_text, is_internal)
           VALUES (?, ?, ?, ?)""",
        (issue_id, staff_id, note_text, is_internal)
    )

    note_type = "Internal note" if is_internal else "Public progress update"
    log_audit(staff_id, "ADD_NOTE", "ISSUE", issue_id, f"{note_type} added")
    flash(f"{note_type} successfully recorded.", "success")
    return redirect(url_for('public.issue_detail', issue_id=issue_id))
