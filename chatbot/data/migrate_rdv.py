"""
Migration : ajoute la table Disponibilites et recrée RendezVous avec nom_patient.
Exécuter depuis chatbot/ : python data/migrate_rdv.py
"""
import os
import sqlite3
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "hopital_fictif.db")

# jour abréviation → numéro (0=lundi, 6=dimanche)
_JOURS = {"Lun": 0, "Mar": 1, "Mer": 2, "Jeu": 3, "Ven": 4, "Sam": 5, "Dim": 6}


def _parse_horraire(horraire):
    """Retourne (jours: list[int], heure_debut, heure_fin) ou None."""
    if not horraire:
        return None
    m = re.match(
        r"(\w{3})(?:-(\w{3}))?\s+(\d{2}:\d{2})-(\d{2}:\d{2})",
        horraire.strip()
    )
    if not m:
        return None
    debut_jour = _JOURS.get(m.group(1))
    fin_jour   = _JOURS.get(m.group(2)) if m.group(2) else debut_jour
    if debut_jour is None or fin_jour is None:
        return None
    jours = list(range(debut_jour, fin_jour + 1))
    return jours, m.group(3), m.group(4)


def migrate():
    conn = sqlite3.connect(DB_PATH)

    # ── 1. Table Disponibilites ──────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Disponibilites (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            id_medecin  INTEGER NOT NULL REFERENCES Medecin(id_medecin),
            jour_semaine INTEGER NOT NULL,   -- 0=lundi … 6=dimanche
            heure_debut TEXT NOT NULL,       -- "09:00"
            heure_fin   TEXT NOT NULL,       -- "17:00"
            duree_min   INTEGER DEFAULT 30
        )
    """)

    # ── 2. Seed Disponibilites depuis Medecin.horraire ──────────────────────
    conn.execute("DELETE FROM Disponibilites")
    medecins = conn.execute(
        "SELECT id_medecin, horraire FROM Medecin"
    ).fetchall()
    rows = []
    for id_med, horraire in medecins:
        parsed = _parse_horraire(horraire or "")
        if not parsed:
            continue
        jours, h_debut, h_fin = parsed
        for jour in jours:
            rows.append((id_med, jour, h_debut, h_fin, 30))
    conn.executemany(
        "INSERT INTO Disponibilites (id_medecin, jour_semaine, heure_debut, heure_fin, duree_min)"
        " VALUES (?,?,?,?,?)",
        rows,
    )

    # ── 3. Recrée RendezVous avec nom_patient + contrainte unicité ──────────
    conn.execute("DROP TABLE IF EXISTS RendezVous")
    conn.execute("""
        CREATE TABLE RendezVous (
            id_rdv      INTEGER PRIMARY KEY AUTOINCREMENT,
            id_medecin  INTEGER NOT NULL REFERENCES Medecin(id_medecin),
            date        TEXT NOT NULL,   -- "2026-05-06"
            heure       TEXT NOT NULL,   -- "09:00"
            nom_patient TEXT NOT NULL,
            UNIQUE(id_medecin, date, heure)
        )
    """)

    conn.commit()
    conn.close()

    print("Migration OK :")
    print(f"  {len(rows)} créneaux de disponibilité insérés")
    print("  Table RendezVous recrée avec contrainte unicité")


if __name__ == "__main__":
    migrate()
