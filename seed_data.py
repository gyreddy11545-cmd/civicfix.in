import os
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'civicfix.db')
SCHEMA_PATH = os.path.join(BASE_DIR, 'schema.sql')

def init_and_seed():
    print(f"Connecting to database at {DB_PATH}...")
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("Removed old database for clean rebuild.")
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Initialize Schema
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    cur = conn.cursor()

    print("Seeding municipal departments...")
    departments = [
        ("Roads, Pavements & Bridges", "ROADS-PWD", "Maintenance of municipal roads, asphalt, potholes and bridges", "roads@civicfix.org"),
        ("Electrical & Street Lighting", "ELEC-LTG", "Streetlight illumination, transformers and smart poles", "electric@civicfix.org"),
        ("Solid Waste Management & Sanitation", "SWM-SAN", "Garbage collection, dumpster clearance and civic hygiene", "sanitation@civicfix.org"),
        ("Storm Water Drainage & Flood Control", "DRAIN-FLD", "Drainage desilting, storm runoff and flood mitigation", "drainage@civicfix.org"),
        ("Water Supply & Sewerage Board", "WATER-SEW", "Potable pipeline supply, leak repair and sewage mains", "water@civicfix.org"),
        ("Parks & Municipal Infrastructure", "PARKS-INF", "Footpaths, public benches, boundary walls and civic parks", "parks@civicfix.org")
    ]
    cur.executemany(
        "INSERT INTO departments (name, code, description, contact_email) VALUES (?, ?, ?, ?)",
        departments
    )
    conn.commit()

    print("Seeding demo users...")
    common_pwd = generate_password_hash("Password@123")
    admin_pwd = generate_password_hash("Admin@123")

    users = [
        # (email, password_hash, full_name, phone, role, department_id, avatar_url)
        ("citizen@civicfix.org", common_pwd, "Ravi Sharma (Citizen)", "+91 98765 43210", "citizen", None, "/static/images/avatars/citizen.png"),
        ("citizen2@civicfix.org", common_pwd, "Priya Nair (Citizen)", "+91 98765 43211", "citizen", None, "/static/images/avatars/citizen2.png"),
        ("staff@civicfix.org", common_pwd, "Vikram Singh (Roads Engineer)", "+91 98765 43220", "staff", 1, "/static/images/avatars/staff.png"),
        ("sanitation@civicfix.org", common_pwd, "Sunita Rao (Sanitation Inspector)", "+91 98765 43221", "staff", 3, "/static/images/avatars/staff2.png"),
        ("electric@civicfix.org", common_pwd, "K. Rajesh (Electrical Officer)", "+91 98765 43222", "staff", 2, "/static/images/avatars/staff3.png"),
        ("admin@civicfix.org", admin_pwd, "Commissioner Ananya Verma (Municipal Admin)", "+91 98765 43299", "admin", None, "/static/images/avatars/admin.png")
    ]
    cur.executemany(
        """INSERT INTO users (email, password_hash, full_name, phone, role, department_id, avatar_url)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        users
    )
    conn.commit()

    now = datetime.utcnow()

    print("Seeding demonstration issues...")
    # Seeded issues:
    # 1. CF-2026-0001: Pothole on main road (Resolved with Before & After photo evidence)
    # 2. CF-2026-0002: Streetlight outage at Junction 7 (In Progress)
    # 3. CF-2026-0003: Overflowing dumpster at Market Road (Assigned)
    # 4. CF-2026-0004: Clogged storm water drain near hospital (Under Review - Critical)
    # 5. CF-2026-0005: Broken footpath pavers (Submitted - New)
    # 6. CF-2026-0006: Duplicate report of Pothole (near Metro Pillar 42, suggested duplicate of CF-2026-0001)

    issues = [
        (
            "CF-2026-0001", "TRK-98412", 1,
            "Deep pothole on main arterial road near Metro Pillar 42",
            "Severe pothole measuring approximately 45cm diameter and 12cm depth. Multiple two-wheelers observed losing balance.",
            "Pothole or damaged road", "High", "High", 78,
            "High traffic corridor near metro transit; direct vehicular safety hazard.",
            "Resolved", 17.4435, 78.3820,
            "Road No. 36, Near Metro Pillar 42, Jubilee Enclave", "Opposite Metro Gate 2",
            1, 3,
            now - timedelta(days=3), now - timedelta(hours=6),
            "Hot mix asphalt applied, steam-roller compacted, safety lane markings repainted.",
            0, None, 1,
            now - timedelta(days=3), now - timedelta(hours=6)
        ),
        (
            "CF-2026-0002", "TRK-98413", 1,
            "Twin LED streetlight outage creating dark zone at Junction 7",
            "Streetlights on pole #J7-14 completely dark for past 3 days. Pedestrian crossing is dark and unsafe at night.",
            "Streetlight failure", "High", "High", 65,
            "Elevated pedestrian safety risk at intersection during night hours.",
            "In Progress", 17.4478, 78.3755,
            "Junction 7, Mindspace Inner Ring Road", "Beside Tech Park Entrance B",
            2, 5,
            now + timedelta(hours=18), None,
            None,
            0, None, 1,
            now - timedelta(days=1, hours=4), now - timedelta(hours=2)
        ),
        (
            "CF-2026-0003", "TRK-98414", 2,
            "Overflowing public dumper bin spilling onto pedestrian footpath",
            "Green municipal bin full to brim. Waste has spilled over 3 meters of pedestrian walkway causing foul odor and stray animal gathering.",
            "Overflowing garbage bin", "Medium", "Medium", 52,
            "Sanitation and hygiene concern along pedestrian transit way.",
            "Assigned", 17.4390, 78.3870,
            "Market Square Road, Madhapur", "In front of Municipal Vegetable Market",
            3, 4,
            now + timedelta(hours=36), None,
            None,
            0, None, 1,
            now - timedelta(hours=14), now - timedelta(hours=5)
        ),
        (
            "CF-2026-0004", "TRK-98415", 1,
            "Severe storm drain blockage with water stagnation near Hospital gate",
            "Storm drain inlet choked with plastic debris. Inflow stopped, resulting in 6 inches of foul waterlogging directly outside hospital casualty entrance.",
            "Drainage blockage", "Critical", "Critical", 92,
            "Emergency hospital ambulance access route compromised; acute flood and health hazard.",
            "Under Review", 17.4510, 78.3700,
            "Care Hospital Approach Road, Gachibowli Corridor", "Emergency Casualty Gate #1",
            4, None,
            now + timedelta(hours=12), None,
            None,
            0, None, 1,
            now - timedelta(hours=6), now - timedelta(hours=6)
        ),
        (
            "CF-2026-0005", "TRK-98416", 2,
            "Broken and collapsed pedestrian concrete pavers near Bus Stop",
            "Multiple interlocking pavers cracked and displaced. Elderly citizens and children frequently trip while boarding public buses.",
            "Broken footpath", "Medium", "Medium", 48,
            "Public bus transit zone; moderate trip and fall liability.",
            "Submitted", 17.4350, 78.3910,
            "Kondapur Main Road, Near Bus Shelter 12", "Adjacent to State Bank Branch",
            6, None,
            now + timedelta(hours=60), None,
            None,
            0, None, 1,
            now - timedelta(hours=2), now - timedelta(hours=2)
        ),
        (
            "CF-2026-0006", "TRK-98417", 2,
            "Hazardous road crater and pothole near Metro Pillar 42",
            "Large pothole in road right next to Metro Pillar 42. Vehicles swerving dangerously into adjacent lane.",
            "Pothole or damaged road", "High", "High", 75,
            "Duplicate candidate for CF-2026-0001 (Identical area & description).",
            "Submitted", 17.4436, 78.3822,
            "Road 36, Metro Pillar 42, Jubilee Enclave, Hyderabad, Telangana", "Near Pillar 42 opposite Metro Gate 2",
            1, None,
            now + timedelta(hours=40), None,
            None,
            0, None, 1,
            now - timedelta(hours=1), now - timedelta(hours=1)
        ),
        # Pan-India Demonstration Records Across Indian States & Union Territories
        (
            "CF-2026-0007", "TRK-98420", 1,
            "Deep asphalt depression on Inner Ring Road near Connaught Place Radial",
            "Dangerous subsidence and asphalt wear causing steering loss for two-wheelers during evening rush hours.",
            "Pothole or damaged road", "High", "High", 82,
            "High density transit corridor in national capital territory.",
            "Resolved", 28.6315, 77.2167,
            "Radial Road 3, Connaught Place, New Delhi, Delhi", "Near Rajiv Chowk Metro Gate 5",
            1, 3,
            now - timedelta(days=2), now - timedelta(hours=5),
            "Cold mix asphalt applied, compacted with vibrating roller, road level restored.",
            0, None, 1,
            now - timedelta(days=2), now - timedelta(hours=5)
        ),
        (
            "CF-2026-0008", "TRK-98421", 2,
            "Major drinking water pipeline rupture flooding pedestrian market road",
            "High-pressure supply pipeline burst with potable water flooding over 50 meters of commercial street.",
            "Water leakage", "High", "High", 80,
            "Substantial potable water loss and transit obstruction in dense suburb.",
            "In Progress", 19.0596, 72.8295,
            "Hill Road, Bandra West, Mumbai, Maharashtra", "Opposite Bandra Police Station",
            5, 4,
            now + timedelta(hours=12), None,
            None,
            0, None, 1,
            now - timedelta(hours=8), now - timedelta(hours=2)
        ),
        (
            "CF-2026-0009", "TRK-98422", 1,
            "Broken and displaced interlocking footpath pavers near bus terminal",
            "Multiple cracked concrete tiles creating severe trip hazard for office commuters and elderly citizens.",
            "Broken footpath", "Medium", "Medium", 58,
            "Key pedestrian access path to transit terminal.",
            "Assigned", 12.9352, 77.6245,
            "100ft Road, 4th Block, Koramangala, Bengaluru, Karnataka", "Near Sony World Signal",
            6, 3,
            now + timedelta(hours=36), None,
            None,
            0, None, 1,
            now - timedelta(hours=18), now - timedelta(hours=4)
        ),
        (
            "CF-2026-0010", "TRK-98423", 2,
            "Overflowing public municipal dumpster spilling into shopping street",
            "Commercial vegetable market bin overflowing for past 48 hours creating public hygiene concern.",
            "Overflowing garbage bin", "Medium", "Medium", 54,
            "High footfall shopping district requiring regular compaction.",
            "Verified", 13.0418, 80.2341,
            "Usman Road, T. Nagar, Chennai, Tamil Nadu", "Near Panagal Park",
            3, None,
            now + timedelta(hours=24), None,
            None,
            0, None, 1,
            now - timedelta(hours=10), now - timedelta(hours=6)
        ),
        (
            "CF-2026-0011", "TRK-98424", 1,
            "Four consecutive streetlights failure causing dark zone at arterial junction",
            "Underground cable short circuit disabled illumination across entire zebra crossing.",
            "Streetlight failure", "High", "High", 72,
            "Nighttime pedestrian road crossing safety compromised.",
            "Submitted", 22.5535, 88.3512,
            "Park Street Crossing, Kolkata, West Bengal", "Near Flurys Intersection",
            2, None,
            now + timedelta(hours=48), None,
            None,
            0, None, 1,
            now - timedelta(hours=4), now - timedelta(hours=4)
        ),
        (
            "CF-2026-0012", "TRK-98425", 2,
            "Clogged storm drainage culvert causing waterlogging near Medical College gate",
            "Heavy plastic accumulation has blocked intake grating; wastewater accumulating outside emergency wing.",
            "Drainage blockage", "Critical", "Critical", 94,
            "Hospital casualty ambulance access route directly impacted.",
            "Under Review", 18.5204, 73.8567,
            "FC Road, Shivajinagar, Pune, Maharashtra", "Near Ferguson College Main Gate",
            4, None,
            now + timedelta(hours=8), None,
            None,
            0, None, 1,
            now - timedelta(hours=3), now - timedelta(hours=3)
        ),
        (
            "CF-2026-0013", "TRK-98426", 1,
            "Broken wrought iron public bench and damaged safety barrier in civic plaza",
            "Public seating collapsed due to structural corrosion; jagged metal edges pose cut hazard.",
            "Damaged public property", "Low", "Low", 36,
            "Cosmetic and public comfort infrastructure.",
            "Assigned", 26.9124, 75.7873,
            "MI Road, Pink City Zone, Jaipur, Rajasthan", "Near Ajmeri Gate",
            6, 3,
            now + timedelta(hours=72), None,
            None,
            0, None, 1,
            now - timedelta(hours=14), now - timedelta(hours=5)
        ),
        (
            "CF-2026-0014", "TRK-98427", 2,
            "Illumination blackout on pedestrian heritage boulevard",
            "Twin cast-iron lamp posts out of order on heritage shopping boulevard.",
            "Streetlight failure", "Medium", "Medium", 60,
            "Heritage tourist promenade night lighting.",
            "Resolved", 26.8467, 80.9462,
            "Hazratganj Main Promenade, Lucknow, Uttar Pradesh", "Near Cathedral School Crossing",
            2, 5,
            now - timedelta(days=1), now - timedelta(hours=4),
            "Fitted new LED retrofit bulbs and replaced damaged underground junction box.",
            0, None, 1,
            now - timedelta(days=1), now - timedelta(hours=4)
        ),
        (
            "CF-2026-0015", "TRK-98428", 1,
            "Dangerous road subsidence and crater on Highway service lane",
            "Significant road depression measuring 60cm across causing heavy trucks and bikes to bounce dangerously.",
            "Pothole or damaged road", "High", "High", 77,
            "High-speed highway connector lane hazard.",
            "In Progress", 23.0338, 72.5074,
            "SG Highway Service Road, Ahmedabad, Gujarat", "Near Iscon Cross Road",
            1, 3,
            now + timedelta(hours=16), None,
            None,
            0, None, 1,
            now - timedelta(hours=12), now - timedelta(hours=2)
        )
    ]

    cur.executemany(
        """INSERT INTO issues (
            id, tracking_code, citizen_id, title, description, category, severity,
            priority_level, priority_score, priority_reason, status, latitude, longitude,
            address, landmark, department_id, assigned_staff_id, target_resolution_at,
            resolved_at, resolution_notes, is_duplicate, primary_issue_id, is_demo,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        issues
    )
    conn.commit()

    print("Seeding issue images (Original & Resolution Evidence)...")
    images = [
        # CF-2026-0001: Pothole Original & Resolution
        ("CF-2026-0001", "original", "/static/uploads/issues/pothole_before.jpg", "pothole_before.jpg", 145000, "Citizen uploaded photograph of road pothole", 1, now - timedelta(days=3)),
        ("CF-2026-0001", "resolution", "/static/uploads/resolutions/pothole_after.jpg", "pothole_after.jpg", 162000, "Municipal Staff resolution proof: Asphalt compaction & yellow lane marking complete", 3, now - timedelta(hours=6)),
        # CF-2026-0002: Streetlight
        ("CF-2026-0002", "original", "/static/uploads/issues/streetlight.jpg", "streetlight.jpg", 128000, "Dark junction streetlight outage", 1, now - timedelta(days=1)),
        # CF-2026-0003: Garbage
        ("CF-2026-0003", "original", "/static/uploads/issues/garbage.jpg", "garbage.jpg", 154000, "Overflowing dumper bin", 2, now - timedelta(hours=14)),
        # CF-2026-0004: Drain
        ("CF-2026-0004", "original", "/static/uploads/issues/drain.jpg", "drain.jpg", 139000, "Blocked stormwater drain with stagnation", 1, now - timedelta(hours=6)),
        # CF-2026-0005: Footpath
        ("CF-2026-0005", "original", "/static/uploads/issues/footpath.jpg", "footpath.jpg", 142000, "Cracked paving blocks near bus shelter", 2, now - timedelta(hours=2)),
        # CF-2026-0006: Duplicate
        ("CF-2026-0006", "original", "/static/uploads/issues/pothole_dup.jpg", "pothole_dup.jpg", 148000, "Second citizen report of road pothole", 2, now - timedelta(hours=1)),
        # Nationwide issues images
        ("CF-2026-0007", "original", "/static/uploads/issues/pothole_before.jpg", "delhi_road.jpg", 152000, "Delhi CP ring road asphalt defect", 1, now - timedelta(days=2)),
        ("CF-2026-0007", "resolution", "/static/uploads/resolutions/pothole_after.jpg", "delhi_repaired.jpg", 158000, "Delhi PWD hot-mix repair proof", 3, now - timedelta(hours=5)),
        ("CF-2026-0008", "original", "/static/uploads/issues/drain.jpg", "mumbai_leak.jpg", 144000, "Mumbai pipe leak street flooding", 2, now - timedelta(hours=8)),
        ("CF-2026-0009", "original", "/static/uploads/issues/footpath.jpg", "bengaluru_footpath.jpg", 141000, "Bengaluru Koramangala footpath tiles", 1, now - timedelta(hours=18)),
        ("CF-2026-0010", "original", "/static/uploads/issues/garbage.jpg", "chennai_bin.jpg", 149000, "Chennai T. Nagar overflowing bin", 2, now - timedelta(hours=10)),
        ("CF-2026-0011", "original", "/static/uploads/issues/streetlight.jpg", "kolkata_lights.jpg", 138000, "Kolkata Park Street junction blackout", 1, now - timedelta(hours=4)),
        ("CF-2026-0012", "original", "/static/uploads/issues/drain.jpg", "pune_drain.jpg", 146000, "Pune FC Road stormwater choking", 2, now - timedelta(hours=3)),
        ("CF-2026-0013", "original", "/static/uploads/issues/footpath.jpg", "jaipur_bench.jpg", 135000, "Jaipur MI road damaged bench", 1, now - timedelta(hours=14)),
        ("CF-2026-0014", "original", "/static/uploads/issues/streetlight.jpg", "lucknow_lamp.jpg", 139000, "Lucknow Hazratganj lamp outage", 2, now - timedelta(days=1)),
        ("CF-2026-0014", "resolution", "/static/uploads/resolutions/pothole_after.jpg", "lucknow_lamp_fixed.jpg", 142000, "Lucknow electrical crew luminaire restored", 5, now - timedelta(hours=4)),
        ("CF-2026-0015", "original", "/static/uploads/issues/pothole_before.jpg", "ahmedabad_road.jpg", 150000, "Ahmedabad SG Highway road depression", 1, now - timedelta(hours=12))
    ]

    cur.executemany(
        """INSERT INTO issue_images (issue_id, image_type, file_path, file_name, file_size, caption, uploaded_by_user_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        images
    )
    conn.commit()

    print("Seeding Civic Trust status audit history...")
    history = [
        # CF-2026-0001 complete workflow
        ("CF-2026-0001", None, "Submitted", 1, "Citizen filed report via Mobile Camera with GPS coordinates", now - timedelta(days=3)),
        ("CF-2026-0001", "Submitted", "Under Review", 6, "Admin initiated priority evaluation and duplicate check", now - timedelta(days=2, hours=20)),
        ("CF-2026-0001", "Under Review", "Verified", 6, "Field verification confirmed physical pothole severity", now - timedelta(days=2, hours=12)),
        ("CF-2026-0001", "Verified", "Assigned", 6, "Assigned to Roads & Bridges Department Engineer Vikram Singh", now - timedelta(days=2)),
        ("CF-2026-0001", "Assigned", "In Progress", 3, "Maintenance crew dispatched with hot-mix asphalt asphalt machine", now - timedelta(days=1)),
        ("CF-2026-0001", "In Progress", "Resolved", 3, "Repairs completed. Fresh asphalt compacted and safety markers painted. Resolution evidence uploaded.", now - timedelta(hours=6)),
        # CF-2026-0002
        ("CF-2026-0002", None, "Submitted", 1, "Citizen filed streetlight failure report", now - timedelta(days=1, hours=4)),
        ("CF-2026-0002", "Submitted", "Verified", 6, "Electrical zone staff verified luminaire capacitor failure", now - timedelta(days=1)),
        ("CF-2026-0002", "Verified", "Assigned", 6, "Assigned to Electrical Officer K. Rajesh", now - timedelta(hours=18)),
        ("CF-2026-0002", "Assigned", "In Progress", 5, "Bucket truck on site replacing LED ballast and cables", now - timedelta(hours=2))
    ]
    cur.executemany(
        """INSERT INTO issue_status_history (issue_id, from_status, to_status, changed_by_user_id, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        history
    )
    conn.commit()

    print("Seeding duplicate link recommendation...")
    # CF-2026-0006 is a suggested duplicate of CF-2026-0001
    cur.execute(
        """INSERT INTO duplicate_links (
            primary_issue_id, duplicate_issue_id, similarity_score, similarity_breakdown,
            status, reviewed_by_user_id, merge_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "CF-2026-0001", "CF-2026-0006", 88,
            '{"category_score": 25, "geo_score": 35, "text_score": 20, "time_score": 8, "distance_meters": 22.4, "text_similarity_pct": 42.5}',
            "suggested", None, None, now - timedelta(minutes=45)
        )
    )
    conn.commit()

    print("Seeding citizen feedback and community confirmations...")
    # CF-2026-0001 Citizen feedback
    cur.execute(
        """INSERT INTO citizen_feedback (issue_id, citizen_id, rating, feedback_text, confirmed_resolved, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("CF-2026-0001", 1, 5, "Excellent response time! Road was completely repaired within 48 hours. Thank you CivicFix!", 1, now - timedelta(hours=4))
    )
    # Community confirmations
    cur.execute(
        """INSERT INTO community_confirmations (issue_id, user_id, confirmed_fixed, created_at)
           VALUES (?, ?, 1, ?)""",
        ("CF-2026-0001", 1, now - timedelta(hours=4))
    )
    cur.execute(
        """INSERT INTO community_confirmations (issue_id, user_id, confirmed_fixed, created_at)
           VALUES (?, ?, 1, ?)""",
        ("CF-2026-0001", 2, now - timedelta(hours=3))
    )

    print("Seeding notifications...")
    notifications = [
        (1, "CF-2026-0001", "Issue Resolved Successfully!", "Your reported pothole on Road No. 36 has been resolved with verified photo proof. Please confirm resolution.", "resolved", 0, now - timedelta(hours=6)),
        (1, "CF-2026-0002", "Status Update: In Progress", "Repairs on your reported streetlight at Junction 7 have commenced with crew on site.", "in_progress", 0, now - timedelta(hours=2)),
        (3, "CF-2026-0001", "Work Order Assigned", "You were assigned issue CF-2026-0001 by Municipal Administration.", "assignment", 1, now - timedelta(days=2))
    ]
    cur.executemany(
        """INSERT INTO notifications (user_id, issue_id, title, message, notification_type, is_read, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        notifications
    )

    print("Seeding audit logs...")
    cur.execute(
        """INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (6, "SYSTEM_INIT", "SYSTEM", "0", "CivicFix system initialized with Innovators Conclave 2026 demonstration dataset", "127.0.0.1", now - timedelta(days=3))
    )

    conn.commit()
    conn.close()
    print("Database seeding completed successfully!")

if __name__ == '__main__':
    init_and_seed()
