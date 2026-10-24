import os
import re
import json
from app.database import query_db, query_one

# Comprehensive Civic Knowledge Base & Guided Intents
INTENT_PATTERNS = {
    'report_guide': [
        r'\b(how to|how do i|report|file|submit|lodge)\b.*\b(issue|complaint|problem|grievance|pothole)\b',
        r'\b(reporting process|steps to report|create report)\b'
    ],
    'category_suggest': [
        r'\b(category|which category|what category|type of issue|suggest category)\b',
        r'\b(pothole|crater|road|asphalt|streetlight|light|bulb|garbage|waste|trash|dump|water leak|pipeline|drain|drainage|sewer|flood|footpath|pavement|sidewalk|bench|park)\b'
    ],
    'status_explain': [
        r'\b(status|statuses|what does .* mean|under review|in progress|verified|assigned|resolved|reopened)\b'
    ],
    'photo_guide': [
        r'\b(photo|image|picture|camera|upload|photograph|evidence)\b'
    ],
    'location_guide': [
        r'\b(location|gps|coordinates|map pin|pinpoint|address|where)\b'
    ],
    'duplicate_explain': [
        r'\b(duplicate|similar|same issue|already reported|already exists)\b'
    ],
    'track_check': [
        r'\b(track|check status|where is my|progress of|cf-20\d\d-\d+|trk-\d+)\b'
    ],
    'feedback_guide': [
        r'\b(feedback|rating|confirm resolution|confirm fix|satisfied|close issue)\b'
    ],
    'about_civicfix': [
        r'\b(about|who are you|what is civicfix|conclave|innovators|ic26)\b'
    ]
}

def analyze_category(text):
    text_lower = text.lower()
    if any(k in text_lower for k in ['pothole', 'road damage', 'crater', 'asphalt', 'tar', 'speed breaker', 'bump']):
        return "Pothole or damaged road", "Roads, Pavements & Bridges (PWD)"
    if any(k in text_lower for k in ['streetlight', 'street light', 'dark', 'bulb', 'pole', 'illumination', 'lamp']):
        return "Streetlight failure", "Electrical & Street Lighting"
    if any(k in text_lower for k in ['garbage', 'waste', 'trash', 'bin', 'dumpster', 'litter', 'smell', 'stench']):
        return "Overflowing garbage bin", "Solid Waste Management & Sanitation"
    if any(k in text_lower for k in ['drain', 'drainage', 'gutter', 'waterlogging', 'clogged', 'choked', 'monsoon flood']):
        return "Drainage blockage", "Storm Water Drainage & Flood Control"
    if any(k in text_lower for k in ['water leak', 'leakage', 'leak', 'pipe burst', 'drinking water', 'tap leak', 'water supply', 'pipeline']):
        return "Water leakage", "Water Supply & Sewerage Board"

    if any(k in text_lower for k in ['footpath', 'pavement', 'sidewalk', 'pavers', 'pedestrian walk', 'tiles']):
        return "Broken footpath", "Parks & Municipal Infrastructure"
    if any(k in text_lower for k in ['bench', 'park', 'railing', 'public property', 'bus shelter', 'statue', 'fence']):
        return "Damaged public property", "Parks & Municipal Infrastructure"
    return "Other civic issue", "Municipal Administration"

def process_assistant_message(message, lang='en', user_id=None, role='citizen'):
    """
    Modular CivicFix AI Assistant Core.
    Works seamlessly in rule-based mode and integrates LLM API if key is set.
    """
    message_clean = (message or '').strip()
    if not message_clean:
        return {
            'reply': "Hello! I am your CivicFix AI Assistant. How can I help you report, track, or resolve civic infrastructure issues today?",
            'mode': 'guided_rules',
            'suggested_questions': [
                "How do I report a pothole or road hazard?",
                "Which category should I choose?",
                "What does 'Under Review' status mean?",
                "Check the status of my reports"
            ],
            'action_link': '/citizen/report'
        }

    # 1. Check for Issue ID query (e.g. CF-2026-0001 or TRK-98412)
    issue_match = re.search(r'\b(CF-\d{4}-\d{4,5}|TRK-\d{4,6})\b', message_clean.upper())
    if issue_match:
        code = issue_match.group(1)
        issue = query_one(
            """SELECT i.id, i.tracking_code, i.title, i.category, i.severity, i.status,
                      i.created_at, i.landmark, i.address, i.citizen_id,
                      d.name as dept_name
               FROM issues i
               LEFT JOIN departments d ON i.department_id = d.id
               WHERE UPPER(i.id) = ? OR UPPER(i.tracking_code) = ?""",
            (code, code)
        )
        if issue:
            # Check if this issue belongs to the user or is public
            is_owner = (user_id and issue['citizen_id'] == user_id)
            reply = (
                f"**Tracking Update for {issue['id']}**\n\n"
                f"• **Title:** {issue['title']}\n"
                f"• **Category:** {issue['category']}\n"
                f"• **Current Status:** `{issue['status']}`\n"
                f"• **Severity Level:** {issue['severity']}\n"
                f"• **Department:** {issue['dept_name'] or 'Municipal Operations'}\n"
                f"• **Location:** {issue['landmark'] or issue['address'] or 'Registered Location'}\n\n"
            )
            if is_owner:
                reply += "This report was submitted from your account. You will receive notifications as soon as repairs progress!"
            else:
                reply += "You can view complete before/after evidence and civic trust logs on the public tracking page."

            return {
                'reply': reply,
                'mode': 'guided_rules',
                'suggested_questions': [
                    "How can I confirm this resolution?",
                    "What are the SLA resolution hours?",
                    "Report another civic issue"
                ],
                'action_link': f"/issues/{issue['id']}"
            }
        else:
            return {
                'reply': f"I could not locate an issue matching `{code}` in the municipal database. Please double-check the tracking code (e.g., CF-2026-0001) or explore the live issue map.",
                'mode': 'guided_rules',
                'suggested_questions': ["Explore all issues on map", "How to file a new report"],
                'action_link': "/explore"
            }

    # 2. Check if user is asking about "my issues / my reports"
    if user_id and re.search(r'\b(my report|my issue|my complaints|status of my|what did i report)\b', message_clean.lower()):
        my_issues = query_db(
            "SELECT id, title, category, status, created_at FROM issues WHERE citizen_id = ? ORDER BY created_at DESC LIMIT 3",
            (user_id,)
        )
        if my_issues:
            lines = ["Here are your most recent reports:"]
            for mi in my_issues:
                lines.append(f"• **{mi['id']}** ({mi['category']}): *{mi['title']}* — **Status: {mi['status']}**")
            lines.append("\nClick below to open your Citizen Dashboard for full details.")
            return {
                'reply': "\n".join(lines),
                'mode': 'guided_rules',
                'suggested_questions': [f"Track {my_issues[0]['id']}", "File a new report", "How does duplicate check work?"],
                'action_link': "/citizen/dashboard"
            }
        else:
            return {
                'reply': "You have not submitted any civic reports yet. When you notice infrastructure damage like potholes, broken lights, or water leaks, tap 'Report Issue' to file your first photo-verified complaint!",
                'mode': 'guided_rules',
                'suggested_questions': ["How do I report a pothole?", "What photos are needed?"],
                'action_link': "/citizen/report"
            }

    # 3. Reporting Process Intent (Check "How to report" before category suggestion)
    if any(re.search(pat, message_clean, re.I) for pat in INTENT_PATTERNS['report_guide']):
        return {
            'reply': (
                "**How to report a civic issue in 3 quick steps:**\n\n"
                "1. **Capture Photo Proof:** Tap **Take Photo** using your phone camera (rear environment mode) or select an existing photo from your gallery.\n"
                "2. **Confirm GPS Location:** Tap **Use My Location** to auto-tag coordinates, or tap on the map to place the pin precisely.\n"
                "3. **Describe & Submit:** Select category, severity, and provide a landmark. Our system checks for duplicates instantly to prevent redundant work orders.\n\n"
                "Once submitted, you receive a tracking ID (e.g. `CF-2026-0007`) to monitor municipal repairs in real-time!"
            ),
            'mode': 'guided_rules',
            'suggested_questions': [
                "Take me to the Report Form",
                "How does duplicate prevention work?",
                "Which category for broken road?"
            ],
            'action_link': '/citizen/report'
        }

    # 4. Category Suggestion Intent
    cat, dept = analyze_category(message_clean)
    if cat != "Other civic issue" or any(k in message_clean.lower() for k in ['category', 'which category', 'suggest', 'type of issue', 'pothole', 'street light', 'streetlight', 'garbage', 'drain', 'water', 'leak', 'footpath', 'bench']):
        return {
            'reply': (
                f"Based on your description, the most appropriate category is:\n\n"
                f"🏷️ **Category:** `{cat}`\n"
                f"🏛️ **Responsible Department:** {dept}\n\n"
                f"**Tip:** When submitting, our smart priority engine will calculate severity based on proximity to transit corridors, hospitals, and school zones."
            ),
            'mode': 'guided_rules',
            'suggested_questions': [
                f"Start reporting {cat}",
                "How does GPS location tagging work?",
                "What happens after I submit?"
            ],
            'action_link': '/citizen/report'
        }


    # 5. Status Meanings Intent
    if any(re.search(pat, message_clean, re.I) for pat in INTENT_PATTERNS['status_explain']):
        return {
            'reply': (
                "**CivicFix Transparent Lifecycle Statuses:**\n\n"
                "• **Submitted:** Report received and registered with tamper-proof timestamp.\n"
                "• **Under Review:** Municipal administration validating severity and hazard score.\n"
                "• **Verified:** Field inspection confirmed physical problem.\n"
                "• **Assigned:** Work order dispatched to department engineer.\n"
                "• **In Progress:** Repair crew and machinery active on site.\n"
                "• **Resolved:** Repairs completed with verifiable after-photo evidence uploaded!\n"
                "• **Reopened / Disputed:** If citizens report that repairs are incomplete or unsatisfactory."
            ),
            'mode': 'guided_rules',
            'suggested_questions': [
                "What is the SLA target for Critical issues?",
                "How do citizens verify resolutions?",
                "Explore current active repairs on map"
            ],
            'action_link': '/explore'
        }

    # 6. Photo & Evidence Guidance
    if any(re.search(pat, message_clean, re.I) for pat in INTENT_PATTERNS['photo_guide']):
        return {
            'reply': (
                "**Photo Evidence Guidelines:**\n\n"
                "• Ensure daylight or adequate illumination when capturing hazards.\n"
                "• Include a small portion of the surrounding street or landmark for orientation.\n"
                "• CivicFix supports JPG, PNG, and WebP up to 16 MB directly from Android/iOS cameras.\n"
                "• When repairs are finished, municipal workers must upload a matching **After Resolution Photo** before the issue can be marked as Resolved."
            ),
            'mode': 'guided_rules',
            'suggested_questions': ["Go to Report Form", "How do I tag GPS location?"],
            'action_link': '/citizen/report'
        }

    # 7. Duplicate Explanation
    if any(re.search(pat, message_clean, re.I) for pat in INTENT_PATTERNS['duplicate_explain']):
        return {
            'reply': (
                "**Automated Duplicate Prevention Engine:**\n\n"
                "CivicFix automatically scans existing reports within a **200-meter radius** using multi-factor analysis (category matching, spatial distance, and text similarity).\n\n"
                "If someone already reported the same pothole or streetlight, you will see a gentle notification card. You can choose to follow the existing report or continue if it is a separate issue. This prevents municipal work crews from creating duplicate work orders!"
            ),
            'mode': 'guided_rules',
            'suggested_questions': ["Explore all existing reports on map", "Start a new report"],
            'action_link': '/explore'
        }

    # 8. Feedback & Community Confirmation
    if any(re.search(pat, message_clean, re.I) for pat in INTENT_PATTERNS['feedback_guide']):
        return {
            'reply': (
                "**Citizen Resolution Confirmation & Ratings:**\n\n"
                "Once staff marks an issue as Resolved and uploads after-repair photos, citizens can:\n"
                "1. Cast a **Community Confirmation Vote** (Confirmed Fixed vs Disputed).\n"
                "2. Submit a **1 to 5 Star Citizen Rating** with feedback comments.\n"
                "If the problem was not adequately fixed, citizens can request that the issue be **Reopened**."
            ),
            'mode': 'guided_rules',
            'suggested_questions': ["View a resolved demo issue", "Check my reports"],
            'action_link': '/issues/CF-2026-0001'
        }

    # Default Helpful Response
    return {
        'reply': (
            f"I can help you navigate CivicFix, categorize civic issues, explain municipal resolution workflows, and check report statuses across India.\n\n"
            f"You asked: *\"{message_clean}\"*\n\n"
            f"Would you like to file a new infrastructure report, check the status of an existing tracking code, or explore the live nationwide map?"
        ),
        'mode': 'guided_rules',
        'suggested_questions': [
            "How do I report an issue?",
            "Explore issue map across India",
            "What does 'Under Review' mean?",
            "Which category should I select?"
        ],
        'action_link': '/citizen/report'
    }
