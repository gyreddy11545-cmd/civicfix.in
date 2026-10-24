from flask import Blueprint, jsonify, request, g, current_app
from app.database import query_db, query_one
from app.services.duplicate_detector import find_duplicates_for_report, haversine_distance
from app.services.notification import get_user_notifications, mark_notifications_read
from app.services.ai_assistant import process_assistant_message

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/check-duplicates', methods=['POST'])
def check_duplicates_endpoint():
    """Real-time duplicate check endpoint for citizen reporting interface."""
    data = request.get_json() or {}
    category = data.get('category', '')
    title = data.get('title', '')
    description = data.get('description', '')
    lat = data.get('latitude')
    lon = data.get('longitude')

    candidates = find_duplicates_for_report(category, title, description, lat, lon, min_threshold=45)
    
    return jsonify({
        'has_duplicates': len(candidates) > 0,
        'count': len(candidates),
        'candidates': candidates[:3]  # return top 3 matches
    })

@bp.route('/issues/map-data')
def map_data():
    """Public GeoJSON / Marker list for Leaflet interactive map with nationwide Indian filtering."""
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    severity = request.args.get('severity', '').strip()
    state = request.args.get('state', '').strip()
    city = request.args.get('city', '').strip()
    query = request.args.get('q', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    sql = """
        SELECT i.id, i.tracking_code, i.title, i.category, i.severity, i.priority_level, i.status,
               i.latitude, i.longitude, i.address, i.landmark, i.created_at, i.is_demo,
               (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'original' LIMIT 1) as original_image,
               (SELECT file_path FROM issue_images WHERE issue_id = i.id AND image_type = 'resolution' LIMIT 1) as resolution_image
        FROM issues i
        WHERE i.latitude IS NOT NULL AND i.longitude IS NOT NULL
          AND i.is_duplicate = 0
    """
    params = []

    if category:
        sql += " AND i.category = ?"
        params.append(category)
    if status:
        sql += " AND i.status = ?"
        params.append(status)
    if severity:
        sql += " AND (i.severity = ? OR i.priority_level = ?)"
        params.extend([severity, severity])
    if state:
        sql += " AND (i.address LIKE ? OR i.landmark LIKE ?)"
        state_term = f"%{state}%"
        params.extend([state_term, state_term])
    if city:
        sql += " AND (i.address LIKE ? OR i.landmark LIKE ?)"
        city_term = f"%{city}%"
        params.extend([city_term, city_term])
    if query:
        sql += " AND (i.id LIKE ? OR i.tracking_code LIKE ? OR i.title LIKE ? OR i.description LIKE ? OR i.address LIKE ? OR i.landmark LIKE ?)"
        term = f"%{query}%"
        params.extend([term, term, term, term, term, term])
    if date_from:
        sql += " AND date(i.created_at) >= date(?)"
        params.append(date_from)
    if date_to:
        sql += " AND date(i.created_at) <= date(?)"
        params.append(date_to)

    sql += " ORDER BY i.created_at DESC"
    issues = query_db(sql, params)
    
    markers = []
    for issue in issues:
        markers.append({
            'id': issue['id'],
            'tracking_code': issue['tracking_code'],
            'title': issue['title'],
            'category': issue['category'],
            'severity': issue['severity'],
            'priority': issue['priority_level'] or issue['severity'],
            'status': issue['status'],
            'latitude': issue['latitude'],
            'longitude': issue['longitude'],
            'address': issue['address'],
            'landmark': issue['landmark'],
            'created_at': str(issue['created_at'])[:10],
            'is_demo': bool(issue['is_demo']),
            'image_url': issue['original_image'] or '/static/images/placeholder_issue.svg',
            'resolution_url': issue['resolution_image']
        })

    return jsonify({'success': True, 'count': len(markers), 'markers': markers})

@bp.route('/issues/hotspots')
def get_hotspots():
    """
    Urban Issue Hotspots:
    Groups reports by geographic proximity (configurable threshold, default 250m).
    """
    threshold_meters = float(request.args.get('radius', 250))
    
    issues = query_db(
        """SELECT id, title, category, latitude, longitude 
           FROM issues 
           WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND is_duplicate = 0"""
    )
    
    clusters = []
    visited = set()

    for i, issue1 in enumerate(issues):
        if issue1['id'] in visited:
            continue
        cluster_members = [issue1]
        visited.add(issue1['id'])

        for j, issue2 in enumerate(issues):
            if issue2['id'] in visited:
                continue
            dist = haversine_distance(
                issue1['latitude'], issue1['longitude'],
                issue2['latitude'], issue2['longitude']
            )
            if dist is not None and dist <= threshold_meters:
                cluster_members.append(issue2)
                visited.add(issue2['id'])

        if len(cluster_members) >= 2:
            avg_lat = sum(m['latitude'] for m in cluster_members) / len(cluster_members)
            avg_lon = sum(m['longitude'] for m in cluster_members) / len(cluster_members)
            cats = [m['category'] for m in cluster_members]
            dom_cat = max(set(cats), key=cats.count)
            clusters.append({
                'count': len(cluster_members),
                'center_lat': avg_lat,
                'center_lon': avg_lon,
                'dominant_category': dom_cat,
                'issue_ids': [m['id'] for m in cluster_members],
                'radius_meters': threshold_meters
            })

    return jsonify({
        'success': True,
        'threshold_meters': threshold_meters,
        'hotspots': clusters
    })

@bp.route('/notifications')
def notifications_endpoint():
    """Fetch notifications for current authenticated user with image thumbnails."""
    if not g.user:
        return jsonify({'notifications': [], 'unread_count': 0})
    
    filter_mode = request.args.get('filter', 'all')
    unread_only = (filter_mode == 'unread')
    
    notes = get_user_notifications(g.user['id'], limit=30, unread_only=unread_only)
    
    # Also get unread count across all
    all_notes = get_user_notifications(g.user['id'], limit=50, unread_only=False)
    unread_count = sum(1 for n in all_notes if n['is_read'] == 0)
    
    formatted = []
    for n in notes:
        # Pick thumbnail: resolution proof if resolved notification, else original, else None
        thumb = n['resolution_image'] if (n['notification_type'] == 'resolved' and n['resolution_image']) else n['original_image']
        formatted.append({
            'id': n['id'],
            'issue_id': n['issue_id'],
            'title': n['title'],
            'message': n['message'],
            'notification_type': n['notification_type'],
            'is_read': bool(n['is_read']),
            'created_at': str(n['created_at'])[:16],
            'image_url': thumb,
            'category': n['issue_category'] or 'Other civic issue',
            'status': n['issue_status'] or 'Submitted',
            'issue_title': n['issue_title']
        })

    return jsonify({
        'success': True,
        'notifications': formatted,
        'unread_count': unread_count
    })

@bp.route('/notifications/mark-read', methods=['POST'])
def mark_read_endpoint():
    """Mark all or a specific notification as read."""
    if not g.user:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json(silent=True) or {}
    notif_id = data.get('id') or request.args.get('id')
    
    mark_notifications_read(g.user['id'], notif_id)
    return jsonify({'success': True, 'marked_id': notif_id})

@bp.route('/ai-assistant', methods=['POST'])
def ai_assistant_endpoint():
    """
    CivicFix AI Assistant endpoint.
    Answers queries on reporting, categories, statuses, duplicate prevention, and user tracking.
    """
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    lang = data.get('lang', 'en')
    user_id = g.user['id'] if g.user else None
    role = g.user['role'] if g.user else 'citizen'

    response = process_assistant_message(message, lang=lang, user_id=user_id, role=role)
    return jsonify(response)

