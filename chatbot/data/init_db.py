"""
Script d'initialisation de la base de données hospitalière.
Crée les tables et insère des données de démonstration.
Exécuter depuis le dossier chatbot/ : python data/init_db.py
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "hopital.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS Hopital (
    id_hopital  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_hopital TEXT    NOT NULL,
    num_tel     TEXT,
    adresse     TEXT
);

CREATE TABLE IF NOT EXISTS Service (
    id_service  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_service TEXT    NOT NULL,
    id_hopital  INTEGER NOT NULL REFERENCES Hopital(id_hopital),
    localisation TEXT,
    horaire     TEXT
);

CREATE TABLE IF NOT EXISTS Medecin (
    id_medecin  INTEGER PRIMARY KEY AUTOINCREMENT,
    nom_medecin TEXT    NOT NULL,
    specialite  TEXT,
    id_hopital  INTEGER NOT NULL REFERENCES Hopital(id_hopital),
    localisation TEXT,
    horaire     TEXT,
    photo       TEXT
);

CREATE TABLE IF NOT EXISTS Pharmacie (
    id_phar   INTEGER PRIMARY KEY AUTOINCREMENT,
    nom       TEXT    NOT NULL,
    adresse   TEXT,
    distance  REAL,
    horaire   TEXT
);
"""

HOPITAUX = [
    ("Hôpital Central d'Avignon", "04 90 80 33 33", "305 rue Raoul Follereau, 84000 Avignon"),
    ("Clinique Rhône Durance",    "04 90 14 20 20", "250 chemin de Sorguette, 84130 Le Pontet"),
]

SERVICES = [
    # (nom_service, id_hopital, localisation, horaire)
    ("Cardiologie",           1, "Bâtiment A – Étage 2",  "Lun-Ven 08h-18h"),
    ("Urgences",              1, "Bâtiment B – Rez-de-chaussée", "24h/24 7j/7"),
    ("Radiologie",            1, "Bâtiment C – Sous-sol", "Lun-Sam 07h-20h"),
    ("Pédiatrie",             1, "Bâtiment D – Étage 3",  "Lun-Ven 08h-18h"),
    ("Maternité",             1, "Bâtiment E – Étage 1",  "24h/24 7j/7"),
    ("Neurologie",            1, "Bâtiment A – Étage 3",  "Lun-Ven 08h-17h"),
    ("Chirurgie orthopédique",1, "Bâtiment B – Étage 2",  "Lun-Ven 08h-18h"),
    ("Oncologie",             1, "Bâtiment C – Étage 1",  "Lun-Ven 08h-18h"),
    ("Psychiatrie",           1, "Bâtiment F – Étage 1",  "Lun-Ven 09h-17h"),
    ("Admissions",            1, "Bâtiment Principal – Rez-de-chaussée", "Lun-Ven 07h30-18h"),
    ("Cardiologie",           2, "Aile Sud – Étage 1",    "Lun-Ven 08h-17h"),
    ("Radiologie",            2, "Aile Nord – Sous-sol",  "Lun-Sam 08h-19h"),
]

MEDECINS = [
    # (nom_medecin, specialite, id_hopital, localisation, horaire, photo)
    ("Dr. Martin",     "Cardiologie",            1, "Bâtiment A – Étage 2 – Bureau 201", "Lun-Mer 09h-17h", None),
    ("Dr. Dupont",     "Cardiologie",            1, "Bâtiment A – Étage 2 – Bureau 202", "Mar-Jeu 08h-16h", None),
    ("Dr. Bernard",    "Neurologie",             1, "Bâtiment A – Étage 3 – Bureau 305", "Lun-Ven 09h-17h", None),
    ("Dr. Lefevre",    "Pédiatrie",              1, "Bâtiment D – Étage 3 – Bureau 310", "Lun-Ven 08h-18h", None),
    ("Dr. Moreau",     "Oncologie",              1, "Bâtiment C – Étage 1 – Bureau 110", "Lun-Ven 09h-17h", None),
    ("Dr. Simon",      "Chirurgie orthopédique", 1, "Bâtiment B – Étage 2 – Bureau 220", "Mar-Sam 08h-16h", None),
    ("Dr. Laurent",    "Radiologie",             1, "Bâtiment C – Sous-sol – Bureau 01", "Lun-Ven 07h-15h", None),
    ("Dr. Petit",      "Psychiatrie",            1, "Bâtiment F – Étage 1 – Bureau 105", "Lun-Ven 09h-17h", None),
    ("Dr. Garcia",     "Cardiologie",            2, "Aile Sud – Étage 1 – Bureau 104",   "Lun-Jeu 09h-18h", None),
    ("Dr. Thomas",     "Radiologie",             2, "Aile Nord – Sous-sol – Bureau 03",  "Lun-Sam 08h-18h", None),
]

PHARMACIES = [
    # (nom, adresse, distance_km, horaire)
    ("Pharmacie des Remparts",  "12 rue de la République, 84000 Avignon",   0.3, "Lun-Sam 08h-20h"),
    ("Pharmacie du Palais",     "3 place du Palais, 84000 Avignon",         0.7, "Lun-Sam 08h-19h30"),
    ("Pharmacie Saint-Roch",    "45 avenue Saint-Roch, 84000 Avignon",      1.1, "Lun-Sam 08h-20h, Dim 09h-13h"),
    ("Pharmacie Follereau",     "290 rue Raoul Follereau, 84000 Avignon",   0.1, "Lun-Ven 08h30-19h30, Sam 09h-13h"),
]


def init():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Ancienne base supprimée : {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    conn.executemany(
        "INSERT INTO Hopital (nom_hopital, num_tel, adresse) VALUES (?,?,?)",
        HOPITAUX,
    )
    conn.executemany(
        "INSERT INTO Service (nom_service, id_hopital, localisation, horaire) VALUES (?,?,?,?)",
        SERVICES,
    )
    conn.executemany(
        "INSERT INTO Medecin (nom_medecin, specialite, id_hopital, localisation, horaire, photo) VALUES (?,?,?,?,?,?)",
        MEDECINS,
    )
    conn.executemany(
        "INSERT INTO Pharmacie (nom, adresse, distance, horaire) VALUES (?,?,?,?)",
        PHARMACIES,
    )
    conn.commit()
    conn.close()
    print(f"Base créée avec succès : {DB_PATH}")
    print(f"  {len(HOPITAUX)} hôpitaux, {len(SERVICES)} services, {len(MEDECINS)} médecins, {len(PHARMACIES)} pharmacies")


if __name__ == "__main__":
    init()
