from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g, session, jsonify
)
from datetime import datetime
from app.database import query_db, query_one, execute_db, insert_db
from app.services.sla_manager import check_overdue_status
from app.services.audit import log_audit
from app.services.notification import create_notification

bp = Blueprint('public', __name__)

@bp.route('/')
def index():
    """Cinematic Landing Page with Civic Aurora Visual Identity & Live Metrics."""
    # Compute genuine database metrics
    total_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE is_duplicate = 0")['c']
    resolved_issues = query_one("SELECT COUNT(*) as c FROM issues WHERE status = 'Resolved' AND is_duplicate = 0")['c']
    in_progress = query_one("SELECT COUNT(*) as c FROM issues WHERE status IN ('In Progress', 'Assigned', 'Verified') AND is_duplicate = 0")['c']
    total_citizens = query_one("SELECT COUNT(*) as c FROM users WHERE role = 'citizen'")['c']

    # Fetch 4 recent verified/resolved public issues for preview showcase
    recent_issues = query_db(
        """SELECT i.id, i.tracking_code, i.title, i.category, i.severity, i.status,
                  i.landmark, i.created_at, i.is_demo,
                  (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'original' LIMIT 1) as original_image,
                  (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'resolution' LIMIT 1) as resolution_image
           FROM issues i
           WHERE i.is_duplicate = 0
           ORDER BY i.created_at DESC LIMIT 4"""
    )

    stats = {
        'total': total_issues,
        'resolved': resolved_issues,
        'in_progress': in_progress,
        'citizens': total_citizens,
        'resolution_rate': round((resolved_issues / total_issues * 100), 1) if total_issues > 0 else 100
    }

    return render_template('public/index.html', stats=stats, recent_issues=recent_issues)

@bp.route('/explore')
def explore():
    """Interactive Public Issue Map & Directory with Leaflet.js."""
    return render_template('public/explore_map.html')

@bp.route('/track', methods=['GET', 'POST'])
def track():
    """Quick tracking lookup by Issue ID or Tracking Code."""
    query = request.args.get('id') or request.form.get('query', '')
    query = query.strip()
    if not query:
        flash("Please enter an Issue ID (e.g., CF-2026-0001) or Tracking Code.", "warning")
        return redirect(url_for('public.index'))

    issue = query_one(
        "SELECT id FROM issues WHERE UPPER(id) = ? OR UPPER(tracking_code) = ?",
        (query.upper(), query.upper())
    )
    if issue:
        return redirect(url_for('public.issue_detail', issue_id=issue['id']))
    else:
        flash(f"No civic report found matching '{query}'. Please check the ID.", "danger")
        return redirect(url_for('public.index'))

@bp.route('/issues/<issue_id>')
def issue_detail(issue_id):
    """
    Dedicated Issue Detail & Civic Trust Tracking Page.
    Includes Before/After proof, Timeline, Smart Priority explanation,
    Community Confirmation, and Public Comments.
    """
    issue = query_one(
        """SELECT i.*, 
                  u.full_name as citizen_name,
                  d.name as department_name,
                  s.full_name as staff_name,
                  p.id as primary_id, p.title as primary_title
           FROM issues i
           LEFT JOIN users u ON i.citizen_id = u.id
           LEFT JOIN departments d ON i.department_id = d.id
           LEFT JOIN users s ON i.assigned_staff_id = s.id
           LEFT JOIN issues p ON i.primary_issue_id = p.id
           WHERE i.id = ?""",
        (issue_id,)
    )

    if not issue:
        flash(f"Issue {issue_id} not found.", "danger")
        return redirect(url_for('public.index'))

    # Check SLA overdue
    is_overdue, overdue_hours, sla_badge = check_overdue_status(
        issue['created_at'], issue['target_resolution_at'], issue['status']
    )

    # Fetch Images (Original, Resolution Proof, Progress)
    images = query_db(
        "SELECT * FROM issue_images WHERE issue_id = ? ORDER BY created_at ASC",
        (issue_id,)
    )
    original_img = next((img for img in images if img['image_type'] == 'original'), None)
    resolution_img = next((img for img in images if img['image_type'] == 'resolution'), None)

    # Fetch Civic Trust Timeline (Status audit history)
    timeline = query_db(
        """SELECT h.*, u.full_name as author_name, u.role as author_role
           FROM issue_status_history h
           LEFT JOIN users u ON h.changed_by_user_id = u.id
           WHERE h.issue_id = ?
           ORDER BY h.created_at ASC""",
        (issue_id,)
    )

    # Fetch Public Comments (Filter out internal staff notes!)
    comments = query_db(
        """SELECT c.*, u.full_name, u.role
           FROM issue_comments c
           JOIN users u ON c.user_id = u.id
           WHERE c.issue_id = ? AND c.is_internal = 0
           ORDER BY c.created_at ASC""",
        (issue_id,)
    )

    # Community Confirmations count
    confirm_yes = query_one(
        "SELECT COUNT(*) as c FROM community_confirmations WHERE issue_id = ? AND confirmed_fixed = 1",
        (issue_id,)
    )['c']
    confirm_no = query_one(
        "SELECT COUNT(*) as c FROM community_confirmations WHERE issue_id = ? AND confirmed_fixed = 0",
        (issue_id,)
    )['c']

    # User's own confirmation status if logged in
    user_confirmed = None
    if g.user:
        user_vote = query_one(
            "SELECT confirmed_fixed FROM community_confirmations WHERE issue_id = ? AND user_id = ?",
            (issue_id, g.user['id'])
        )
        if user_vote:
            user_confirmed = user_vote['confirmed_fixed']

    # Citizen feedback if resolved
    feedback = query_one(
        "SELECT * FROM citizen_feedback WHERE issue_id = ?",
        (issue_id,)
    )

    # Linked duplicates if this is a primary issue
    linked_duplicates = query_db(
        """SELECT d.id, d.tracking_code, d.title, d.status, dl.similarity_score, dl.created_at
           FROM duplicate_links dl
           JOIN issues d ON dl.duplicate_issue_id = d.id
           WHERE dl.primary_issue_id = ?""",
        (issue_id,)
    )

    return render_template(
        'issue_detail.html',
        issue=issue,
        is_overdue=is_overdue,
        sla_badge=sla_badge,
        original_img=original_img,
        resolution_img=resolution_img,
        images=images,
        timeline=timeline,
        comments=comments,
        confirm_yes=confirm_yes,
        confirm_no=confirm_no,
        user_confirmed=user_confirmed,
        feedback=feedback,
        linked_duplicates=linked_duplicates
    )

@bp.route('/issues/<issue_id>/community-confirm', methods=['POST'])
def community_confirm(issue_id):
    """Allow authenticated citizens/residents to vote whether an issue appears resolved."""
    if not g.user:
        return jsonify({'success': False, 'message': 'Please log in to confirm this repair.'}), 401

    vote = int(request.form.get('vote', 1))  # 1 = fixed, 0 = not fixed
    user_id = g.user['id']

    # Check if already voted
    existing = query_one(
        "SELECT id, confirmed_fixed FROM community_confirmations WHERE issue_id = ? AND user_id = ?",
        (issue_id, user_id)
    )

    if existing:
        execute_db(
            "UPDATE community_confirmations SET confirmed_fixed = ?, created_at = CURRENT_TIMESTAMP WHERE id = ?",
            (vote, existing['id'])
        )
        action_msg = "Updated your confirmation vote."
    else:
        execute_db(
            "INSERT INTO community_confirmations (issue_id, user_id, confirmed_fixed) VALUES (?, ?, ?)",
            (issue_id, user_id, vote)
        )
        action_msg = "Recorded your community confirmation."

    # Return updated totals
    yes_count = query_one("SELECT COUNT(*) as c FROM community_confirmations WHERE issue_id = ? AND confirmed_fixed = 1", (issue_id,))['c']
    no_count = query_one("SELECT COUNT(*) as c FROM community_confirmations WHERE issue_id = ? AND confirmed_fixed = 0", (issue_id,))['c']

    log_audit(user_id, "COMMUNITY_CONFIRM", "ISSUE", issue_id, f"Voted {vote} on resolution status")

    return jsonify({
        'success': True,
        'message': action_msg,
        'yes_count': yes_count,
        'no_count': no_count,
        'user_vote': vote
    })

@bp.route('/issues/<issue_id>/add-comment', methods=['POST'])
def add_comment(issue_id):
    """Add a public citizen/resident comment to an issue."""
    if not g.user:
        flash("Please log in to add a public comment.", "warning")
        return redirect(url_for('public.issue_detail', issue_id=issue_id))

    comment_text = request.form.get('comment_text', '').strip()
    if not comment_text:
        flash("Comment cannot be empty.", "warning")
        return redirect(url_for('public.issue_detail', issue_id=issue_id))

    insert_db(
        "INSERT INTO issue_comments (issue_id, user_id, comment_text, is_internal) VALUES (?, ?, ?, 0)",
        (issue_id, g.user['id'], comment_text)
    )

    log_audit(g.user['id'], "ADD_COMMENT", "ISSUE", issue_id, "Added public comment")
    flash("Your comment has been posted.", "success")
    return redirect(url_for('public.issue_detail', issue_id=issue_id))
