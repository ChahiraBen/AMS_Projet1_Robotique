import sqlite3

conn = sqlite3.connect("hospital.db")
cur = conn.cursor()

# TABLE Hopital
cur.execute("""
CREATE TABLE IF NOT EXISTS Hopital (
    id_hopital INTEGER PRIMARY KEY,
    nom TEXT,
    num_tel TEXT,
    adresse TEXT
)
""")

cur.execute("""
INSERT INTO Hopital VALUES
(1, 'Hopital Central', '01 23 45 67 89', '1 rue de Paris')
""")

# TABLE Service
cur.execute("""
CREATE TABLE IF NOT EXISTS Service (
    id_service INTEGER PRIMARY KEY,
    nom_service TEXT,
    id_hopital INTEGER,
    etage TEXT,
    horaire TEXT
)
""")

cur.executemany("""
INSERT INTO Service VALUES (?, ?, ?, ?, ?)
""", [
    (1, 'cardiologie', 1, '2', '8h-18h'),
    (2, 'radiologie', 1, '1', '8h-17h'),
    (3, 'urgences', 1, 'Rez-de-chaussée', '24h/24')
])

# TABLE Medecin
cur.execute("""
CREATE TABLE IF NOT EXISTS Medecin (
    id_medecin INTEGER PRIMARY KEY,
    nom TEXT,
    id_service INTEGER,
    horaire TEXT,
    photo TEXT
)
""")

cur.executemany("""
INSERT INTO Medecin VALUES (?, ?, ?, ?, ?)
""", [
    (1, 'Martin', 1, '9h-16h', ''),
    (2, 'Dupont', 2, '10h-15h', '')
])

# TABLE Pharmacie
cur.execute("""
CREATE TABLE IF NOT EXISTS Pharmacie (
    id_phar INTEGER PRIMARY KEY,
    nom TEXT,
    adresse TEXT,
    distance REAL,
    horaire TEXT
)
""")

cur.executemany("""
INSERT INTO Pharmacie VALUES (?, ?, ?, ?, ?)
""", [
    (1, 'Pharmacie Gare', '5 rue Victor Hugo', 0.3, '8h-20h'),
    (2, 'Pharmacie Centre', '12 avenue République', 0.5, '9h-19h')
])

conn.commit()
conn.close()

print("Base de données hospital.db créée avec succès.")
