import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ISSUES_DIR = os.path.join(BASE_DIR, 'app', 'static', 'uploads', 'issues')
RESOLUTIONS_DIR = os.path.join(BASE_DIR, 'app', 'static', 'uploads', 'resolutions')

os.makedirs(ISSUES_DIR, exist_ok=True)
os.makedirs(RESOLUTIONS_DIR, exist_ok=True)

def create_banner_image(path, title, subtitle, bg_color1, bg_color2, accent_color, is_resolved=False):
    width, height = 800, 500
    img = Image.new('RGB', (width, height), bg_color1)
    draw = ImageDraw.Draw(img)

    # Gradient background simulation
    r1, g1, b1 = bg_color1
    r2, g2, b2 = bg_color2
    for y in range(height):
        ratio = y / height
        nr = int(r1 * (1 - ratio) + r2 * ratio)
        ng = int(g1 * (1 - ratio) + g2 * ratio)
        nb = int(b1 * (1 - ratio) + b2 * ratio)
        draw.line([(0, y), (width, y)], fill=(nr, ng, nb))

    # Grid lines / urban pattern
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(nr + 15, ng + 15, nb + 15), width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(nr + 15, ng + 15, nb + 15), width=1)

    # Center illustration box
    draw.rounded_rectangle([60, 60, width - 60, height - 60], radius=16, outline=accent_color, width=3)

    # Status ribbon / tag
    badge_color = (52, 211, 153) if is_resolved else (251, 113, 133)
    badge_text = "[VERIFIED RESOLUTION EVIDENCE]" if is_resolved else "[CIVIC INFRASTRUCTURE REPORT]"
    draw.rectangle([80, 80, 480, 120], fill=badge_color)
    draw.text((95, 92), badge_text, fill=(15, 23, 42))

    # Title & description text
    draw.text((90, 160), title, fill=(241, 245, 249))
    draw.text((90, 210), subtitle, fill=(148, 163, 184))
    
    # Metadata footer
    draw.line([(90, 360), (width - 90, 360)], fill=(100, 116, 139), width=1)
    status_label = "STATUS: RESOLVED & VERIFIED" if is_resolved else "STATUS: CITIZEN REPORTED"
    draw.text((90, 380), f"{status_label} | MUNICIPAL AUDIT TRAIL", fill=accent_color)
    draw.text((90, 410), "Geo-tagged: Cyberabad Zone 4, Hi-Tech City Corridor", fill=(148, 163, 184))

    img.save(path, 'JPEG', quality=90)
    print(f"Generated {path}")

def generate_all():
    # 1. Pothole Before
    create_banner_image(
        os.path.join(ISSUES_DIR, 'pothole_before.jpg'),
        "DEEP POTHOLE ON MAIN ARTERIAL ROAD",
        "Pothole ~45cm diameter, 12cm deep near Metro Pillar 42. Poses accident risk.",
        (40, 44, 52), (25, 28, 36), (251, 191, 36)
    )

    # 2. Pothole After (Resolution)
    create_banner_image(
        os.path.join(RESOLUTIONS_DIR, 'pothole_after.jpg'),
        "ROAD RESURFACED & POTHOLE SEALED",
        "Hot mix asphalt applied, compacted, and yellow safety lane marking restored.",
        (20, 40, 35), (10, 25, 20), (52, 211, 153), is_resolved=True
    )

    # 3. Duplicate Pothole report
    create_banner_image(
        os.path.join(ISSUES_DIR, 'pothole_dup.jpg'),
        "HAZARDOUS ROAD CRATER / POTHOLE",
        "Large pothole near Pillar 42, vehicles swerving into oncoming lane.",
        (45, 42, 50), (28, 26, 35), (251, 113, 133)
    )

    # 4. Streetlight failure
    create_banner_image(
        os.path.join(ISSUES_DIR, 'streetlight.jpg'),
        "STREETLIGHT OUTAGE AT JUNCTION 7",
        "Twin LED luminaire dark for 3 consecutive nights. Pedestrian safety issue.",
        (15, 23, 42), (2, 6, 23), (34, 211, 238)
    )

    # 5. Garbage overflow
    create_banner_image(
        os.path.join(ISSUES_DIR, 'garbage.jpg'),
        "OVERFLOWING DUMPSTER AT MARKET ROAD",
        "Municipal dumper bin filled to brim; solid waste spilling onto pedestrian sidewalk.",
        (50, 40, 30), (30, 20, 15), (251, 146, 60)
    )

    # 6. Blocked drain
    create_banner_image(
        os.path.join(ISSUES_DIR, 'drain.jpg'),
        "CLOGGED STORM WATER DRAINAGE GRATE",
        "Plastic debris blocking storm runoff inlet; 6 inches of water stagnation.",
        (20, 35, 55), (12, 22, 38), (45, 212, 191)
    )

    # 7. Broken footpath
    create_banner_image(
        os.path.join(ISSUES_DIR, 'footpath.jpg'),
        "COLLAPSED CONCRETE PAVING SLABS",
        "Cracked pedestrian paver blocks creating trip hazard near public bus shelter.",
        (45, 45, 45), (25, 25, 25), (167, 139, 250)
    )

if __name__ == '__main__':
    generate_all()
