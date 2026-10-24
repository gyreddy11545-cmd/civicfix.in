import re

# High-risk civic hazard keywords that raise safety urgency
CRITICAL_SAFETY_KEYWORDS = {
    'school': 15,
    'hospital': 18,
    'clinic': 12,
    'bus stand': 12,
    'bus stop': 10,
    'metro': 12,
    'highway': 15,
    'sparking': 25,
    'exposed wire': 25,
    'electric shock': 30,
    'accident': 20,
    'elderly': 12,
    'children': 15,
    'flood': 18,
    'waterlogging': 15,
    'deep pothole': 15,
    'caved in': 20,
    'collapse': 22,
    'overflowing sewage': 15,
    'toxic': 20,
    'gas': 22
}

CATEGORY_BASE_SCORES = {
    "Pothole or damaged road": 25,
    "Drainage blockage": 25,
    "Water leakage": 22,
    "Streetlight failure": 20,
    "Broken footpath": 18,
    "Overflowing garbage bin": 15,
    "Damaged public property": 15,
    "Other civic issue": 10
}

SEVERITY_SCORES = {
    "Critical": 40,
    "High": 25,
    "Medium": 15,
    "Low": 5
}

def calculate_priority_recommendation(category, severity, title="", description="", landmark=""):
    """
    Calculate an explainable priority recommendation based on:
    - Civic Category baseline
    - Declared Citizen Severity
    - Environmental / Safety hazard keyword detection
    Returns: (recommended_priority, priority_score, explanation_str)
    """
    base_category_score = CATEGORY_BASE_SCORES.get(category, 15)
    severity_score = SEVERITY_SCORES.get(severity, 15)
    
    total_score = base_category_score + severity_score
    reasons = [
        f"Category '{category}' base weight ({base_category_score} pts)",
        f"Declared citizen severity '{severity}' ({severity_score} pts)"
    ]
    
    # Keyword analysis across title, description, and landmark
    combined_text = f"{title} {description} {landmark}".lower()
    matched_keywords = []
    keyword_points = 0
    
    for kw, weight in CRITICAL_SAFETY_KEYWORDS.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', combined_text):
            matched_keywords.append((kw, weight))
            keyword_points += weight
    
    if matched_keywords:
        # Cap keyword bonus at 35 points to avoid runaway scoring
        keyword_points = min(keyword_points, 35)
        total_score += keyword_points
        kw_list_str = ", ".join([f"'{kw}' (+{w})" for kw, w in matched_keywords[:3]])
        reasons.append(f"Identified elevated safety indicators: {kw_list_str}")
        
    # Cap total score at 100
    final_score = min(total_score, 100)
    
    # Map score to explainable recommended priority tier
    if final_score >= 80:
        recommended = "Critical"
        urgency_label = "Immediate Municipal Attention Required"
    elif final_score >= 60:
        recommended = "High"
        urgency_label = "Elevated Civic Priority"
    elif final_score >= 40:
        recommended = "Medium"
        urgency_label = "Standard Operational Priority"
    else:
        recommended = "Low"
        urgency_label = "Routine Maintenance Schedule"
        
    explanation = f"{urgency_label} (Score: {final_score}/100). {'; '.join(reasons)}."
    
    return recommended, final_score, explanation
