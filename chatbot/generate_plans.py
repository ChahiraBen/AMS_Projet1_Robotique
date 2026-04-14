"""
Génère les SVG de plan d'hôpital pour chaque service.
Execute : python generate_plans.py
"""
import os

OUTPUT_DIR = os.path.join("static", "img", "plans")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BLUE       = "#0056b3"
BLUE_LIGHT = "#e8f0fe"
GRAY_BG    = "#f4f6f9"
WHITE      = "#ffffff"
GRAY_TEXT  = "#555555"
HIGHLIGHT  = "#0056b3"
HIGHLIGHT_TEXT = "#ffffff"

# Tous les étages (du bas vers le haut dans l'affichage SVG = haut vers bas)
FLOORS = [
    (4, "Étage 4",  "Maternité"),
    (3, "Étage 3",  "Pédiatrie"),
    (2, "Étage 2",  "Cardiologie"),
    (1, "Étage 1",  "Radiologie"),
    (0, "R.D.C.",   "Urgences"),
]

# Service → fichier SVG
SERVICES = {
    "urgences":    0,
    "radiologie":  1,
    "cardiologie": 2,
    "pediatrie":   3,
    "maternite":   4,
}

W = 480
FLOOR_H = 52
FLOOR_X = 100
FLOOR_W = 300
START_Y = 55
ELEVATOR_X = 420


def make_svg(highlight_floor):
    lines = []
    total_h = START_Y + len(FLOORS) * FLOOR_H + 40

    lines.append(
        '<svg width="{}" height="{}" xmlns="http://www.w3.org/2000/svg" '
        'font-family="Arial,sans-serif">'.format(W, total_h)
    )
    lines.append('<rect width="{}" height="{}" fill="{}"/>'.format(W, total_h, GRAY_BG))

    # Titre
    lines.append(
        '<text x="{}" y="32" text-anchor="middle" font-size="15" '
        'font-weight="bold" fill="{}">Plan de l\'hôpital</text>'.format(W // 2, BLUE)
    )

    # Étages (du haut vers le bas dans le SVG = étage 4 en haut)
    for i, (floor_num, floor_label, service_name) in enumerate(FLOORS):
        y = START_Y + i * FLOOR_H
        is_target = (floor_num == highlight_floor)

        fill   = HIGHLIGHT      if is_target else WHITE
        stroke = BLUE           if is_target else "#cccccc"
        sw     = "2"            if is_target else "1"
        tcolor = HIGHLIGHT_TEXT if is_target else GRAY_TEXT
        scolor = HIGHLIGHT_TEXT if is_target else BLUE

        # Rectangle étage
        lines.append(
            '<rect x="{}" y="{}" width="{}" height="{}" '
            'fill="{}" stroke="{}" stroke-width="{}" rx="4"/>'.format(
                FLOOR_X, y, FLOOR_W, FLOOR_H - 4, fill, stroke, sw
            )
        )

        # Label étage (gauche)
        lines.append(
            '<text x="{}" y="{}" font-size="11" fill="{}">{}</text>'.format(
                FLOOR_X + 10, y + (FLOOR_H - 4) // 2 + 4, tcolor, floor_label
            )
        )

        # Nom du service (centre)
        lines.append(
            '<text x="{}" y="{}" text-anchor="middle" font-size="13" '
            'font-weight="{}" fill="{}">{}</text>'.format(
                FLOOR_X + FLOOR_W // 2, y + (FLOOR_H - 4) // 2 + 4,
                "bold" if is_target else "normal",
                scolor, service_name
            )
        )

        # Flèche sur l'étage cible
        if is_target:
            ax = FLOOR_X + FLOOR_W - 30
            ay = y + (FLOOR_H - 4) // 2
            lines.append(
                '<text x="{}" y="{}" font-size="18" fill="{}">&#9654;</text>'.format(
                    ax, ay + 6, HIGHLIGHT_TEXT
                )
            )

    # Ascenseur
    elev_y = START_Y
    elev_h = len(FLOORS) * FLOOR_H - 4
    lines.append(
        '<rect x="{}" y="{}" width="32" height="{}" '
        'fill="{}" stroke="{}" stroke-width="1" rx="4"/>'.format(
            ELEVATOR_X, elev_y, elev_h, BLUE_LIGHT, BLUE
        )
    )
    lines.append(
        '<text x="{}" y="{}" text-anchor="middle" font-size="10" fill="{}">🛗</text>'.format(
            ELEVATOR_X + 16, elev_y + 20, BLUE
        )
    )
    lines.append(
        '<text x="{}" y="{}" text-anchor="middle" font-size="9" fill="{}">Ascenseur</text>'.format(
            ELEVATOR_X + 16, elev_y + elev_h + 14, GRAY_TEXT
        )
    )

    lines.append("</svg>")
    return "\n".join(lines)


for service_slug, floor_num in SERVICES.items():
    svg_content = make_svg(floor_num)
    path = os.path.join(OUTPUT_DIR, "plan_{}.svg".format(service_slug))
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print("Généré : {}".format(path))

print("Terminé.")
