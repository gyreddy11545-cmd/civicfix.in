import os
import random
import string
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g, session, current_app, jsonify
)
from app.routes.auth import login_required
from app.database import query_db, query_one, execute_db, insert_db
from app.services.priority_engine import calculate_priority_recommendation
from app.services.sla_manager import calculate_target_resolution
from app.services.duplicate_detector import find_duplicates_for_report
from app.services.audit import log_audit
from app.services.notification import create_notification

bp = Blueprint('citizen', __name__, url_prefix='/citizen')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def generate_unique_issue_id():
    """Generate next sequential issue ID like CF-2026-0007."""
    year = datetime.utcnow().year
    prefix = f"CF-{year}-"
    # Find highest current number
    row = query_one(
        "SELECT id FROM issues WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{prefix}%",)
    )
    if row and row['id']:
        try:
            num = int(row['id'].split('-')[-1]) + 1
        except Exception:
            num = 1
    else:
        num = 1
    return f"{prefix}{num:04d}"

def generate_tracking_code():
    """Generate randomized tracking code like TRK-84912."""
    rand = ''.join(random.choices(string.digits, k=5))
    return f"TRK-{rand}"

@bp.route('/dashboard')
@login_required
def dashboard():
    user_id = g.user['id']

    # Citizen statistics from real database records
    total_reports = query_one(
        "SELECT COUNT(*) as c FROM issues WHERE citizen_id = ? AND is_duplicate = 0",
        (user_id,)
    )['c']

    awaiting_verification = query_one(
        "SELECT COUNT(*) as c FROM issues WHERE citizen_id = ? AND status IN ('Submitted', 'Under Review') AND is_duplicate = 0",
        (user_id,)
    )['c']

    in_progress = query_one(
        "SELECT COUNT(*) as c FROM issues WHERE citizen_id = ? AND status IN ('Verified', 'Assigned', 'In Progress') AND is_duplicate = 0",
        (user_id,)
    )['c']

    resolved = query_one(
        "SELECT COUNT(*) as c FROM issues WHERE citizen_id = ? AND status = 'Resolved' AND is_duplicate = 0",
        (user_id,)
    )['c']

    # Fetch user's issues with filter options
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')
    search_query = request.args.get('q', '').strip()

    sql = """
        SELECT i.*, 
               (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'original' LIMIT 1) as original_image,
               (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'resolution' LIMIT 1) as resolution_image
        FROM issues i
        WHERE i.citizen_id = ?
    """
    params = [user_id]

    if status_filter:
        sql += " AND i.status = ?"
        params.append(status_filter)
    if category_filter:
        sql += " AND i.category = ?"
        params.append(category_filter)
    if search_query:
        sql += " AND (i.id LIKE ? OR i.title LIKE ? OR i.description LIKE ? OR i.tracking_code LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term, term])

    sql += " ORDER BY i.created_at DESC"
    my_issues = query_db(sql, params)

    # Fetch recent unread notifications
    notifications = query_db(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )

    return render_template(
        'citizen/dashboard.html',
        stats={
            'total': total_reports,
            'awaiting': awaiting_verification,
            'in_progress': in_progress,
            'resolved': resolved
        },
        issues=my_issues,
        notifications=notifications,
        categories=current_app.config['CATEGORIES']
    )

@bp.route('/report', methods=['GET', 'POST'])
def report_issue():
    """
    Complete Civic Issue Reporting Workflow.
    Supports real mobile camera capture (capture="environment"), gallery upload,
    Leaflet GPS coordinates, automatic Smart Priority recommendation,
    and intelligent duplicate detection.
    """
    # Allow anonymous view of report page, but prompt login on submission or auto-associate
    categories = current_app.config['CATEGORIES']
    severities = current_app.config['SEVERITY_LEVELS']

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        severity = request.form.get('severity', 'Medium').strip()
        lat_str = request.form.get('latitude', '').strip()
        lon_str = request.form.get('longitude', '').strip()
        address = request.form.get('address', '').strip()
        landmark = request.form.get('landmark', '').strip()
        bypass_duplicate = request.form.get('bypass_duplicate', '0') == '1'

        if not title or not description or not category:
            flash("Please provide a Title, Description, and Category for the civic issue.", "danger")
            return render_template('citizen/report.html', categories=categories, severities=severities)

        lat = None
        lon = None
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                pass

        # Check for possible duplicates before persisting unless explicitly bypassed
        if not bypass_duplicate:
            duplicates = find_duplicates_for_report(category, title, description, lat, lon, min_threshold=55)
            if duplicates and len(duplicates) > 0:
                top_match = duplicates[0]
                # If high confidence duplicate, return response indicating duplicate prompt
                return render_template(
                    'citizen/report.html',
                    categories=categories,
                    severities=severities,
                    duplicate_prompt=True,
                    top_duplicate=top_match,
                    form_data={
                        'title': title,
                        'description': description,
                        'category': category,
                        'severity': severity,
                        'latitude': lat_str,
                        'longitude': lon_str,
                        'address': address,
                        'landmark': landmark
                    }
                )

        # Handle File Upload (Real Mobile Camera / Gallery)
        file = None
        for f in request.files.getlist('photo'):
            if f and f.filename and f.filename.strip():
                file = f
                break

        file_path = None
        orig_filename = None
        file_size = 0

        if file and file.filename != '':
            if not allowed_file(file.filename):
                flash("Unsupported file format. Please upload JPG, PNG, WEBP, or HEIC image.", "danger")
                return render_template('citizen/report.html', categories=categories, severities=severities)

            orig_filename = secure_filename(file.filename)
            unique_name = f"issue_{int(datetime.utcnow().timestamp())}_{orig_filename}"
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'issues', unique_name)
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file.save(save_path)
            file_size = os.path.getsize(save_path)
            max_limit = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
            if file_size > max_limit:
                try:
                    os.remove(save_path)
                except Exception:
                    pass
                flash("Uploaded photograph exceeds maximum file size limit (16MB).", "danger")
                return render_template('citizen/report.html', categories=categories, severities=severities)
            file_path = f"/static/uploads/issues/{unique_name}"

        # Generate Unique Issue ID & Tracking Code
        issue_id = generate_unique_issue_id()
        tracking_code = generate_tracking_code()
        citizen_id = g.user['id'] if g.user else None

        # Calculate Smart Priority Recommendation
        rec_priority, priority_score, priority_reason = calculate_priority_recommendation(
            category=category,
            severity=severity,
            title=title,
            description=description,
            landmark=landmark
        )

        # Calculate SLA target resolution time
        now = datetime.utcnow()
        target_resolution = calculate_target_resolution(now, rec_priority)

        # Department mapping suggestion
        dept_map = {
            "Pothole or damaged road": 1,
            "Streetlight failure": 2,
            "Overflowing garbage bin": 3,
            "Drainage blockage": 4,
            "Water leakage": 5,
            "Broken footpath": 6,
            "Damaged public property": 6,
            "Other civic issue": 1
        }
        dept_id = dept_map.get(category, 1)

        # Persist issue to database
        execute_db(
            """INSERT INTO issues (
                id, tracking_code, citizen_id, title, description, category, severity,
                priority_level, priority_score, priority_reason, status, latitude, longitude,
                address, landmark, department_id, target_resolution_at, is_demo, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
            (
                issue_id, tracking_code, citizen_id, title, description, category, severity,
                rec_priority, priority_score, priority_reason, lat, lon,
                address, landmark, dept_id, target_resolution
            )
        )

        # Persist Photo Attachment if uploaded
        if file_path:
            execute_db(
                """INSERT INTO issue_images (issue_id, image_type, file_path, file_name, file_size, caption, uploaded_by_user_id)
                   VALUES (?, 'original', ?, ?, ?, 'Citizen mobile photo capture', ?)""",
                (issue_id, file_path, orig_filename, file_size, citizen_id)
            )

        # Record initial status history event
        execute_db(
            """INSERT INTO issue_status_history (issue_id, from_status, to_status, changed_by_user_id, notes)
               VALUES (?, NULL, 'Submitted', ?, 'Report submitted by citizen via CivicFix mobile interface')""",
            (issue_id, citizen_id)
        )

        # Create user notification if logged in
        if citizen_id:
            create_notification(
                citizen_id, issue_id,
                "Report Submitted Successfully",
                f"Your report {issue_id} has been submitted and queued for municipal verification.",
                "submitted"
            )

        log_audit(citizen_id, "CREATE_ISSUE", "ISSUE", issue_id, f"Created {category} report: {title}")

        flash(f"Civic report successfully submitted! Your Tracking ID is {issue_id}.", "success")
        return redirect(url_for('public.issue_detail', issue_id=issue_id))

    return render_template('citizen/report.html', categories=categories, severities=severities)

@bp.route('/issues/<issue_id>/feedback', methods=['POST'])
@login_required
def submit_feedback(issue_id):
    """Citizen rating (1-5 stars) and feedback comment on completed resolution."""
    rating = int(request.form.get('rating', 5))
    feedback_text = request.form.get('feedback_text', '').strip()
    confirmed = int(request.form.get('confirmed_resolved', 1))

    # Check if already submitted
    existing = query_one(
        "SELECT id FROM citizen_feedback WHERE issue_id = ? AND citizen_id = ?",
        (issue_id, g.user['id'])
    )

    if existing:
        execute_db(
            """UPDATE citizen_feedback 
               SET rating = ?, feedback_text = ?, confirmed_resolved = ?, created_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (rating, feedback_text, confirmed, existing['id'])
        )
    else:
        execute_db(
            """INSERT INTO citizen_feedback (issue_id, citizen_id, rating, feedback_text, confirmed_resolved)
               VALUES (?, ?, ?, ?, ?)""",
            (issue_id, g.user['id'], rating, feedback_text, confirmed)
        )

    log_audit(g.user['id'], "SUBMIT_FEEDBACK", "ISSUE", issue_id, f"Rating {rating}/5 submitted")
    flash("Thank you! Your feedback has been recorded for the municipal service team.", "success")
    return redirect(url_for('public.issue_detail', issue_id=issue_id))

@bp.route('/issues/<issue_id>/reopen', methods=['POST'])
@login_required
def reopen_issue(issue_id):
    """Citizen request to reopen an issue if repair is unsatisfactory."""
    reopen_reason = request.form.get('reopen_reason', '').strip()
    if not reopen_reason:
        flash("Please provide a specific reason for requesting reopening.", "warning")
        return redirect(url_for('public.issue_detail', issue_id=issue_id))

    issue = query_one("SELECT status FROM issues WHERE id = ?", (issue_id,))
    if not issue or issue['status'] != 'Resolved':
        flash("Only resolved issues can be reopened.", "danger")
        return redirect(url_for('public.issue_detail', issue_id=issue_id))

    execute_db(
        """UPDATE issues 
           SET status = 'Reopened', reopen_reason = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (reopen_reason, issue_id)
    )

    execute_db(
        """INSERT INTO issue_status_history (issue_id, from_status, to_status, changed_by_user_id, notes)
           VALUES (?, 'Resolved', 'Reopened', ?, ?)""",
        (issue_id, g.user['id'], f"Reopened by citizen: {reopen_reason}")
    )

    log_audit(g.user['id'], "REOPEN_ISSUE", "ISSUE", issue_id, f"Reopened: {reopen_reason}")
    flash("Issue has been reopened and escalated to municipal administration.", "warning")
    return redirect(url_for('public.issue_detail', issue_id=issue_id))
