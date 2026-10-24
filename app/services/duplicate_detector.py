import math
import re
from datetime import datetime, timedelta
from app.database import query_db, execute_db, insert_db

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in meters.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (ValueError, TypeError):
        return None

    # Radius of earth in meters
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def tokenize(text):
    """Normalize and tokenize text into words, removing basic stopwords."""
    if not text:
        return set()
    stopwords = {'the', 'a', 'an', 'in', 'on', 'at', 'near', 'by', 'of', 'and', 'or', 'is', 'to', 'for', 'with', 'from', 'it'}
    words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', text.lower())
    return set(w for w in words if w not in stopwords)

def calculate_text_similarity(text1, text2):
    """Calculate Jaccard similarity of normalized word tokens."""
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union) if union else 0.0

def evaluate_duplicate(new_category, new_title, new_desc, new_lat, new_lon, existing_issue):
    """
    Evaluate duplicate similarity score (0 to 100) between a new report and an existing issue.
    Returns: (score, breakdown_dict, reasons_list)
    """
    score = 0
    breakdown = {
        'category_score': 0,
        'geo_score': 0,
        'text_score': 0,
        'time_score': 0,
        'distance_meters': None,
        'text_similarity_pct': 0
    }
    reasons = []

    # 1. Category comparison (25 pts)
    if new_category and existing_issue['category'] and new_category.strip().lower() == existing_issue['category'].strip().lower():
        score += 25
        breakdown['category_score'] = 25
        reasons.append(f"Identical civic category: '{new_category}' (+25 pts)")
    else:
        # Different category means highly unlikely to be the same exact physical issue
        # We do not penalize to 0 immediately in case of miscategorization, but cap max score
        pass

    # 2. Geographic proximity (up to 35 pts)
    dist = haversine_distance(new_lat, new_lon, existing_issue['latitude'], existing_issue['longitude'])
    if dist is not None:
        breakdown['distance_meters'] = round(dist, 1)
        if dist <= 30:
            score += 35
            breakdown['geo_score'] = 35
            reasons.append(f"Immediate proximity: within {round(dist)}m (+35 pts)")
        elif dist <= 80:
            score += 25
            breakdown['geo_score'] = 25
            reasons.append(f"Close proximity: {round(dist)}m away (+25 pts)")
        elif dist <= 200:
            score += 15
            breakdown['geo_score'] = 15
            reasons.append(f"Moderate proximity: {round(dist)}m away (+15 pts)")
        elif dist <= 400:
            score += 5
            breakdown['geo_score'] = 5
            reasons.append(f"Same neighbourhood: {round(dist)}m away (+5 pts)")
        else:
            reasons.append(f"Geographically distant: {round(dist)}m away (0 pts)")
    elif new_lat is None or existing_issue['latitude'] is None:
        reasons.append("GPS coordinates not available on both records for geo-check")

    # 3. Text description & title overlap (up to 30 pts)
    full_new = f"{new_title or ''} {new_desc or ''}"
    full_exist = f"{existing_issue['title'] or ''} {existing_issue['description'] or ''}"
    sim = calculate_text_similarity(full_new, full_exist)
    sim_pct = round(sim * 100, 1)
    breakdown['text_similarity_pct'] = sim_pct

    if sim >= 0.5:
        score += 30
        breakdown['text_score'] = 30
        reasons.append(f"High phrasing overlap: {sim_pct}% matching key tokens (+30 pts)")
    elif sim >= 0.25:
        score += 20
        breakdown['text_score'] = 20
        reasons.append(f"Moderate phrasing overlap: {sim_pct}% matching key tokens (+20 pts)")
    elif sim >= 0.12:
        score += 10
        breakdown['text_score'] = 10
        reasons.append(f"Some overlapping keywords: {sim_pct}% (+10 pts)")

    # 4. Submission time window (up to 10 pts)
    # Active issues filed within last 14 days are much more likely duplicates
    try:
        created_str = str(existing_issue['created_at'])
        # Handle formats e.g. "2026-10-23 12:00:00" or ISO
        dt = datetime.strptime(created_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
        days_ago = (datetime.utcnow() - dt).days
        if days_ago <= 14 and existing_issue['status'] not in ('Resolved', 'Rejected'):
            score += 10
            breakdown['time_score'] = 10
            reasons.append(f"Reported recently ({days_ago} days ago) and currently unresolved (+10 pts)")
    except Exception:
        pass

    # Cap score at 100
    final_score = min(score, 100)
    return final_score, breakdown, reasons

def find_duplicates_for_report(category, title, description, lat, lon, exclude_id=None, min_threshold=45):
    """
    Search database for potential duplicates against open or recently active issues.
    Returns list of candidate dicts sorted by similarity score descending.
    """
    query = """
        SELECT id, tracking_code, title, description, category, severity, status,
               latitude, longitude, address, landmark, created_at
        FROM issues
        WHERE status NOT IN ('Resolved', 'Rejected')
          AND is_duplicate = 0
    """
    args = []
    if exclude_id:
        query += " AND id != ?"
        args.append(exclude_id)
    
    candidates = query_db(query, args)
    results = []

    for item in candidates:
        score, breakdown, reasons = evaluate_duplicate(
            category, title, description, lat, lon, item
        )
        if score >= min_threshold:
            # fetch original image if available
            img = query_db(
                "SELECT file_path FROM issue_images WHERE issue_id = ? AND image_type = 'original' LIMIT 1",
                (item['id'],),
                one=True
            )
            results.append({
                'issue_id': item['id'],
                'tracking_code': item['tracking_code'],
                'title': item['title'],
                'description': item['description'],
                'category': item['category'],
                'severity': item['severity'],
                'status': item['status'],
                'address': item['address'],
                'landmark': item['landmark'],
                'created_at': str(item['created_at']),
                'score': score,
                'breakdown': breakdown,
                'reasons': reasons,
                'image_path': img['file_path'] if img else None
            })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def merge_duplicate_issue(primary_id, duplicate_id, admin_user_id, reason="Confirmed duplicate by municipal admin"):
    """
    Merge a duplicate issue into a primary issue:
    1. Mark duplicate issue as is_duplicate = 1 and primary_issue_id = primary_id.
    2. Insert or update duplicate_links table with status = 'confirmed'.
    3. Update audit log.
    4. Add a status history entry to the duplicate issue.
    """
    # Verify both exist
    primary = query_db("SELECT id, title FROM issues WHERE id = ?", (primary_id,), one=True)
    dup = query_db("SELECT id, title, status FROM issues WHERE id = ?", (duplicate_id,), one=True)
    if not primary or not dup:
        return False, "One or both issues not found"

    # Mark duplicate in issues table
    execute_db(
        """UPDATE issues 
           SET is_duplicate = 1, primary_issue_id = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (primary_id, duplicate_id)
    )

    # Check if duplicate_link already exists
    existing_link = query_db(
        "SELECT id FROM duplicate_links WHERE primary_issue_id = ? AND duplicate_issue_id = ?",
        (primary_id, duplicate_id),
        one=True
    )
    if existing_link:
        execute_db(
            """UPDATE duplicate_links 
               SET status = 'confirmed', reviewed_by_user_id = ?, merge_reason = ?, reviewed_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (admin_user_id, reason, existing_link['id'])
        )
    else:
        execute_db(
            """INSERT INTO duplicate_links 
               (primary_issue_id, duplicate_issue_id, similarity_score, similarity_breakdown, status, reviewed_by_user_id, merge_reason, reviewed_at)
               VALUES (?, ?, 100, '{"manual_merge": true}', 'confirmed', ?, ?, CURRENT_TIMESTAMP)""",
            (primary_id, duplicate_id, admin_user_id, reason)
        )

    # Add status history
    execute_db(
        """INSERT INTO issue_status_history (issue_id, from_status, to_status, changed_by_user_id, notes)
           VALUES (?, ?, ?, ?, ?)""",
        (duplicate_id, dup['status'], 'Merged Duplicate', admin_user_id, f"Merged into primary issue {primary_id}. Reason: {reason}")
    )

    return True, f"Successfully merged {duplicate_id} into {primary_id}"
