import os
import unittest
import json
import io
from app import create_app
from app.database import get_db, init_db, query_one, query_db, execute_db
from app.config import Config
from app.services.duplicate_detector import evaluate_duplicate, find_duplicates_for_report, merge_duplicate_issue
from app.services.priority_engine import calculate_priority_recommendation
from app.services.sla_manager import calculate_target_resolution, check_overdue_status

class TestConfig(Config):
    TESTING = True
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_civicfix.db')
    SECRET_KEY = 'test-secret-key'

class CivicFixTestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TestConfig.DATABASE_PATH):
            try:
                os.remove(TestConfig.DATABASE_PATH)
            except Exception:
                pass
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        with self.app.app_context():
            # Run schema
            init_db()
            # Seed test users
            from werkzeug.security import generate_password_hash
            pwd = generate_password_hash("Password@123")
            admin_pwd = generate_password_hash("Admin@123")

            execute_db("DELETE FROM duplicate_links;")
            execute_db("DELETE FROM issue_images;")
            execute_db("DELETE FROM issue_status_history;")
            execute_db("DELETE FROM issues;")
            execute_db("DELETE FROM users;")
            execute_db("DELETE FROM departments;")

            execute_db(
                "INSERT INTO departments (id, name, code, description) VALUES (1, 'Roads & Infrastructure', 'ROADS', 'Road maintenance')"
            )
            execute_db(
                """INSERT INTO users (id, email, password_hash, full_name, role, department_id)
                   VALUES (1, 'citizen@civicfix.org', ?, 'Ravi Sharma', 'citizen', NULL)""",
                (pwd,)
            )
            execute_db(
                """INSERT INTO users (id, email, password_hash, full_name, role, department_id)
                   VALUES (2, 'staff@civicfix.org', ?, 'Vikram Singh', 'staff', 1)""",
                (pwd,)
            )
            execute_db(
                """INSERT INTO users (id, email, password_hash, full_name, role, department_id)
                   VALUES (3, 'admin@civicfix.org', ?, 'Commissioner Verma', 'admin', NULL)""",
                (admin_pwd,)
            )

    def tearDown(self):
        with self.app.app_context():
            if os.path.exists(TestConfig.DATABASE_PATH):
                pass # keep or remove

    def test_01_public_landing_page(self):
        """Verify public landing page loads with HTTP 200."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'CivicFix', res.data)
        self.assertIn(b'REPORT IT', res.data)

    def test_02_demo_logins(self):
        """Verify 1-click demonstration logins for Citizen, Staff, and Administrator."""
        # Citizen demo login
        res = self.client.get('/auth/demo-login/citizen', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Ravi Sharma', res.data)

        # Staff demo login
        res = self.client.get('/auth/demo-login/staff', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Staff Command', res.data)

        # Admin demo login
        res = self.client.get('/auth/demo-login/admin', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Municipal Administrator', res.data)

    def test_03_smart_priority_recommendation(self):
        """Verify explainable priority score calculation and hazard detection."""
        # Critical case near hospital
        rec, score, reason = calculate_priority_recommendation(
            category="Drainage blockage",
            severity="Critical",
            title="Severe storm drain flooding near hospital casualty gate",
            description="6 inches of stagnant sewage outside emergency entrance",
            landmark="Near Care Hospital"
        )
        self.assertEqual(rec, "Critical")
        self.assertGreaterEqual(score, 80)
        self.assertIn("hospital", reason.lower())

        # Routine case
        rec_low, score_low, _ = calculate_priority_recommendation(
            category="Other civic issue",
            severity="Low",
            title="Park bench paint chipped",
            description="Minor cosmetic wear",
            landmark=""
        )
        self.assertEqual(rec_low, "Low")
        self.assertLess(score_low, 40)

    def test_04_issue_reporting_workflow(self):
        """Verify report creation, photo upload simulation, and unique ID generation."""
        # Log in as citizen
        self.client.get('/auth/demo-login/citizen')

        # Submit issue with coordinates
        img_data = (io.BytesIO(b"fake image bytes"), 'test_pothole.jpg')
        res = self.client.post('/citizen/report', data={
            'title': 'Dangerous road crater near Metro Pillar 10',
            'description': 'Vehicles swerving dangerously into oncoming traffic lane.',
            'category': 'Pothole or damaged road',
            'severity': 'High',
            'latitude': '17.4435',
            'longitude': '78.3820',
            'landmark': 'Metro Pillar 10',
            'address': 'Madhapur Main Road',
            'photo': img_data
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Dangerous road crater', res.data)
        
        # Verify in database
        with self.app.app_context():
            issue = query_one("SELECT * FROM issues WHERE title LIKE '%Pillar 10%'")
            self.assertIsNotNone(issue)
            self.assertTrue(issue['id'].startswith('CF-'))
            self.assertEqual(issue['status'], 'Submitted')
            self.assertEqual(issue['latitude'], 17.4435)

            # Check status history was logged
            history = query_db("SELECT * FROM issue_status_history WHERE issue_id = ?", (issue['id'],))
            self.assertGreaterEqual(len(history), 1)

    def test_05_duplicate_detection_engine(self):
        """Verify multi-factor similarity score and candidate flagging."""
        with self.app.app_context():
            # Seed base issue
            execute_db(
                """INSERT INTO issues (id, tracking_code, citizen_id, title, description, category, severity, status, latitude, longitude, is_duplicate)
                   VALUES ('CF-2026-0099', 'TRK-99001', 1, 'Deep pothole on Road 36 near pillar 42',
                           'Hazardous pothole causing two-wheelers to fall.', 'Pothole or damaged road', 'High', 'Submitted', 17.4435, 78.3820, 0)"""
            )

        # Test duplicate check API with near identical report (25m away)
        res = self.client.post('/api/check-duplicates', json={
            'category': 'Pothole or damaged road',
            'title': 'Severe pothole road 36 metro pillar 42',
            'description': 'Two-wheelers losing balance due to deep pothole.',
            'latitude': 17.4437,
            'longitude': 78.3821
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['has_duplicates'])
        self.assertGreaterEqual(data['candidates'][0]['score'], 60)
        self.assertEqual(data['candidates'][0]['issue_id'], 'CF-2026-0099')

    def test_06_staff_status_workflow_and_resolution(self):
        """Verify municipal staff transitions and resolution photo proof submission."""
        with self.app.app_context():
            execute_db(
                """INSERT INTO issues (id, tracking_code, citizen_id, title, description, category, severity, status, department_id, assigned_staff_id, is_duplicate)
                   VALUES ('CF-2026-0050', 'TRK-50001', 1, 'Broken street luminaire', 'Dark crossing', 'Streetlight failure', 'High', 'Assigned', 1, 2, 0)"""
            )

        # Log in as staff
        self.client.get('/auth/demo-login/staff')

        # Update status to In Progress
        res = self.client.post('/staff/issues/CF-2026-0050/update-status', data={
            'status': 'In Progress',
            'notes': 'Maintenance team on site with replacement LED bulb'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Submit Resolution Evidence
        res_img = (io.BytesIO(b"fake resolution image bytes"), 'resolved_light.jpg')
        res_resolve = self.client.post('/staff/issues/CF-2026-0050/resolve', data={
            'resolution_description': 'New 120W LED luminaire mounted and tested. Illumination verified.',
            'resolution_photo': res_img
        }, follow_redirects=True)
        self.assertEqual(res_resolve.status_code, 200)

        # Verify DB state
        with self.app.app_context():
            issue = query_one("SELECT status, resolved_at, resolution_notes FROM issues WHERE id = 'CF-2026-0050'")
            self.assertEqual(issue['status'], 'Resolved')
            self.assertIsNotNone(issue['resolved_at'])

            # Verify resolution image link
            img = query_one("SELECT * FROM issue_images WHERE issue_id = 'CF-2026-0050' AND image_type = 'resolution'")
            self.assertIsNotNone(img)

    def test_07_community_confirmation_and_feedback(self):
        """Verify resident community confirmation voting and rating feedback."""
        with self.app.app_context():
            execute_db(
                """INSERT INTO issues (id, tracking_code, citizen_id, title, description, category, severity, status, is_duplicate)
                   VALUES ('CF-2026-0077', 'TRK-77001', 1, 'Footpath repaired', 'Fixed pavers', 'Broken footpath', 'Medium', 'Resolved', 0)"""
            )

        # Log in as citizen
        self.client.get('/auth/demo-login/citizen')

        # Vote confirmed fixed
        res = self.client.post('/issues/CF-2026-0077/community-confirm', data={'vote': '1'})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['yes_count'], 1)

        # Submit citizen satisfaction feedback
        res_fb = self.client.post('/citizen/issues/CF-2026-0077/feedback', data={
            'rating': '5',
            'feedback_text': 'Great job fixing the pavement so promptly!',
            'confirmed_resolved': '1'
        }, follow_redirects=True)
        self.assertEqual(res_fb.status_code, 200)

        with self.app.app_context():
            fb = query_one("SELECT * FROM citizen_feedback WHERE issue_id = 'CF-2026-0077'")
            self.assertIsNotNone(fb)
            self.assertEqual(fb['rating'], 5)

    def test_08_admin_duplicate_merge(self):
        """Verify administrator merging duplicate into primary record."""
        with self.app.app_context():
            execute_db(
                """INSERT INTO issues (id, tracking_code, citizen_id, title, description, category, severity, status, is_duplicate)
                   VALUES ('CF-2026-0080', 'TRK-80001', 1, 'Primary Pothole', 'Desc 1', 'Pothole or damaged road', 'High', 'Verified', 0)"""
            )
            execute_db(
                """INSERT INTO issues (id, tracking_code, citizen_id, title, description, category, severity, status, is_duplicate)
                   VALUES ('CF-2026-0081', 'TRK-80002', 1, 'Duplicate Pothole', 'Desc 2', 'Pothole or damaged road', 'High', 'Submitted', 0)"""
            )
            execute_db(
                """INSERT INTO duplicate_links (id, primary_issue_id, duplicate_issue_id, similarity_score, status)
                   VALUES (1, 'CF-2026-0080', 'CF-2026-0081', 85, 'suggested')"""
            )

        self.client.get('/auth/demo-login/admin')
        res = self.client.post('/admin/duplicate-review/1', data={
            'action': 'confirm',
            'reason': 'Verified duplicate complaint on identical spot'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            dup = query_one("SELECT is_duplicate, primary_issue_id FROM issues WHERE id = 'CF-2026-0081'")
            self.assertEqual(dup['is_duplicate'], 1)
            self.assertEqual(dup['primary_issue_id'], 'CF-2026-0080')

    def test_09_csv_export(self):
        """Verify real CSV dataset export."""
        self.client.get('/auth/demo-login/admin')
        res = self.client.get('/admin/export-csv')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'text/csv')
        self.assertIn(b'Issue ID,Tracking Code,Title', res.data)

    def test_10_ai_assistant_api(self):
        """Verify CivicFix AI Assistant responses for category suggestions and reporting guidance."""
        # Test category suggestion
        res = self.client.post('/api/ai-assistant', json={
            'message': 'There is a severe water pipeline leakage flooding the street'
        })
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn('Water leakage', data['reply'])
        self.assertEqual(data['mode'], 'guided_rules')

        # Test reporting process explanation
        res_guide = self.client.post('/api/ai-assistant', json={
            'message': 'How do I report a pothole?'
        })
        self.assertEqual(res_guide.status_code, 200)
        data_guide = json.loads(res_guide.data)
        self.assertIn('Capture Photo Proof', data_guide['reply'])
        self.assertIn('Use My Location', data_guide['reply'])

    def test_11_notifications_circular_and_mark_read(self):
        """Verify rich notifications API with image metadata and mark-read support."""
        with self.app.app_context():
            # Seed an issue with an image and notification
            execute_db(
                """INSERT INTO issues (id, tracking_code, citizen_id, title, description, category, severity, status)
                   VALUES ('CF-2026-0095', 'TRK-95001', 1, 'Pothole test', 'Desc', 'Pothole or damaged road', 'High', 'Submitted')"""
            )
            execute_db(
                """INSERT INTO issue_images (issue_id, image_type, file_path, file_name)
                   VALUES ('CF-2026-0095', 'original', '/static/uploads/issues/test.jpg', 'test.jpg')"""
            )
            execute_db(
                """INSERT INTO notifications (id, user_id, issue_id, title, message, notification_type, is_read)
                   VALUES (95, 1, 'CF-2026-0095', 'Issue Under Review', 'Staff assigned', 'status_update', 0)"""
            )

        # Login as citizen
        self.client.get('/auth/demo-login/citizen')

        # Fetch notifications
        res = self.client.get('/api/notifications?filter=unread')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertGreaterEqual(data['unread_count'], 1)
        found = any(n['issue_id'] == 'CF-2026-0095' for n in data['notifications'])
        self.assertTrue(found)

        # Mark single notification as read
        res_mark = self.client.post('/api/notifications/mark-read', json={'id': 95})
        self.assertEqual(res_mark.status_code, 200)

        with self.app.app_context():
            notif = query_one("SELECT is_read FROM notifications WHERE id = 95")
            self.assertEqual(notif['is_read'], 1)

    def test_12_nationwide_map_filtering(self):
        """Verify nationwide map data endpoint with state, city, and status filters."""
        with self.app.app_context():
            execute_db(
                """INSERT INTO issues (id, tracking_code, citizen_id, title, description, category, severity, status, latitude, longitude, address, landmark, is_duplicate)
                   VALUES ('CF-2026-0090', 'TRK-90001', 1, 'Delhi CP Road', 'Pothole in CP', 'Pothole or damaged road', 'High', 'Resolved', 28.6315, 77.2167, 'Connaught Place, New Delhi, Delhi', 'Near Metro', 0)"""
            )

        # Filter by state Delhi
        res = self.client.get('/api/issues/map-data?state=Delhi')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        delhi_markers = [m for m in data['markers'] if m['id'] == 'CF-2026-0090']
        self.assertEqual(len(delhi_markers), 1)
        self.assertEqual(delhi_markers[0]['status'], 'Resolved')

if __name__ == '__main__':
    unittest.main()

