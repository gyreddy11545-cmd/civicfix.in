from app.database import execute_db, query_db

def create_notification(user_id, issue_id, title, message, notification_type="status_update"):
    """Create an in-app notification for a citizen or staff member."""
    if not user_id:
        return
    try:
        execute_db(
            """INSERT INTO notifications (user_id, issue_id, title, message, notification_type, is_read)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (user_id, issue_id, title, message, notification_type)
        )
    except Exception as e:
        print(f"Error creating notification: {e}")

def get_user_notifications(user_id, limit=20, unread_only=False):
    """Fetch unread and recent notifications for a user with rich issue metadata."""
    sql = """
        SELECT n.id, n.issue_id, n.title, n.message, n.notification_type, n.is_read, n.created_at,
               (SELECT file_path FROM issue_images WHERE issue_id = n.issue_id AND image_type = 'original' LIMIT 1) as original_image,
               (SELECT file_path FROM issue_images WHERE issue_id = n.issue_id AND image_type = 'resolution' LIMIT 1) as resolution_image,
               i.category as issue_category,
               i.status as issue_status,
               i.title as issue_title
        FROM notifications n
        LEFT JOIN issues i ON n.issue_id = i.id
        WHERE n.user_id = ?
    """
    params = [user_id]
    if unread_only:
        sql += " AND n.is_read = 0"
    sql += " ORDER BY n.created_at DESC LIMIT ?"
    params.append(limit)
    return query_db(sql, params)

def mark_notifications_read(user_id, notification_id=None):
    """Mark all or a specific notification as read for a user."""
    if notification_id:
        execute_db(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND id = ?",
            (user_id, notification_id)
        )
    else:
        execute_db(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
            (user_id,)
        )

