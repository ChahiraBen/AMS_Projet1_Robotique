from repositories.db import query_all, query_one
from repositories.db import get_connection


class RDVRepository:

    def find_doctors_by_specialite(self, specialite):
        sql = """
        SELECT m.id_medecin,
               (m.prenom || ' ' || m.nom) AS nom_medecin,
               m.specialite, m.horraire, m.disponible,
               s.nom_service
        FROM Medecin m
        LEFT JOIN Service s ON m.id_service = s.id_service
        WHERE m.specialite LIKE ? AND m.disponible = 1
        """
        return query_all(sql, (f"%{specialite}%",))

    def find_doctor_by_name(self, name):
        sql = """
        SELECT m.id_medecin,
               (m.prenom || ' ' || m.nom) AS nom_medecin,
               m.specialite, m.horraire, m.disponible,
               s.nom_service
        FROM Medecin m
        LEFT JOIN Service s ON m.id_service = s.id_service
        WHERE (m.nom LIKE ? OR m.prenom LIKE ?) AND m.disponible = 1
        """
        return query_all(sql, (f"%{name}%", f"%{name}%"))

    def find_patient(self, nom, prenom):
        sql = "SELECT id_patient FROM Patient WHERE nom = ? AND prenom = ?"
        return query_one(sql, (nom.strip().upper(), prenom.strip().capitalize()))

    def create_patient(self, nom, prenom):
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO Patient (nom, prenom) VALUES (?, ?)",
            (nom.strip().upper(), prenom.strip().capitalize())
        )
        conn.commit()
        patient_id = c.lastrowid
        conn.close()
        return patient_id

    def get_or_create_patient(self, nom, prenom):
        row = self.find_patient(nom, prenom)
        if row:
            return row["id_patient"]
        return self.create_patient(nom, prenom)

    def get_booked_slots(self, id_medecin, date):
        """Retourne les heures déjà réservées pour un médecin à une date donnée."""
        sql = "SELECT heure FROM RendezVous WHERE id_medecin = ? AND date = ?"
        rows = query_all(sql, (id_medecin, date))
        return [r["heure"] for r in rows]

    def get_doctor_hours(self, id_medecin):
        """Retourne le champ horraire du médecin."""
        row = query_one("SELECT horraire FROM Medecin WHERE id_medecin = ?", (id_medecin,))
        return row["horraire"] if row else None

    def is_slot_taken(self, id_medecin, date, heure):
        row = query_one(
            "SELECT id_rdv FROM RendezVous WHERE id_medecin = ? AND date = ? AND heure = ?",
            (id_medecin, date, heure)
        )
        return row is not None

    def create_rdv(self, id_patient, id_medecin, date, heure):
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO RendezVous (id_patient, id_medecin, date, heure) VALUES (?, ?, ?, ?)",
            (id_patient, id_medecin, date, heure)
        )
        conn.commit()
        rdv_id = c.lastrowid
        conn.close()
        return rdv_id
