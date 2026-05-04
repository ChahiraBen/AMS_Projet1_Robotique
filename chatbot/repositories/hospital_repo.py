import re
from datetime import datetime, timedelta
from repositories.db import query_one, query_all, get_connection

_MOIS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12, "décembre": 12,
}


def _parse_date(s):
    """Accepte YYYY-MM-DD, DD/MM, DD/MM/YYYY, '5 mai', '5 mai 2026'."""
    s = s.strip().lower()
    # YYYY-MM-DD
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    # DD/MM ou DD/MM/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?$", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else datetime.today().year
        try:
            return datetime(y, mo, d).date()
        except ValueError:
            pass
    # "5 mai" ou "le 5 mai 2026"
    m = re.search(r"(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", s)
    if m:
        d = int(m.group(1))
        mo = _MOIS.get(m.group(2))
        y = int(m.group(3)) if m.group(3) else datetime.today().year
        if mo:
            try:
                return datetime(y, mo, d).date()
            except ValueError:
                pass
    return None


class HospitalRepository:

    # ── Localisation / horaires / contacts ──────────────────────────────────

    def find_service_location(self, service_name):
        return query_all(
            "SELECT nom_service, etage, horraire FROM Service WHERE nom_service LIKE ?",
            (f"%{service_name}%",),
        )

    def find_doctor_location(self, doctor_name):
        import re
        doctor_name = re.sub(r"^(dr\.?\s*|docteur\s*)", "", doctor_name.strip(), flags=re.IGNORECASE).strip()
        p = f"%{doctor_name}%"
        return query_all(
            """SELECT (m.prenom || ' ' || m.nom) AS nom_medecin,
                      m.specialite, m.horraire,
                      s.nom_service AS service
               FROM Medecin m LEFT JOIN Service s ON m.id_service = s.id_service
               WHERE m.nom LIKE ? OR m.prenom LIKE ?
                  OR (m.prenom || ' ' || m.nom) LIKE ?
                  OR (m.nom || ' ' || m.prenom) LIKE ?""",
            (p, p, p, p),
        )

    def find_service_hours(self, service_name):
        return query_all(
            "SELECT nom_service, horraire FROM Service WHERE nom_service LIKE ?",
            (f"%{service_name}%",),
        )

    def find_service_contact(self, service_name):
        return query_all(
            """SELECT s.nom_service, h.nom AS hopital, h.num_tel, h.adresse
               FROM Service s JOIN Hopital h ON s.id_service = h.id_hopital
               WHERE s.nom_service LIKE ? LIMIT 1""",
            (f"%{service_name}%",),
        )

    def find_all_services(self):
        return query_all("SELECT nom_service, etage, horraire FROM Service ORDER BY nom_service")

    def find_all_doctors(self, nom_service=None):
        if nom_service:
            return query_all(
                """SELECT (m.prenom || ' ' || m.nom) AS nom_medecin,
                          m.specialite, s.nom_service AS service
                   FROM Medecin m LEFT JOIN Service s ON m.id_service = s.id_service
                   WHERE s.nom_service LIKE ? OR m.specialite LIKE ?
                   ORDER BY m.nom""",
                (f"%{nom_service}%", f"%{nom_service}%"),
            )
        return query_all(
            """SELECT (m.prenom || ' ' || m.nom) AS nom_medecin,
                      m.specialite, s.nom_service AS service
               FROM Medecin m LEFT JOIN Service s ON m.id_service = s.id_service
               ORDER BY m.nom"""
        )

    def find_nearest_pharmacies(self):
        return query_all(
            "SELECT nom, adresse, telephone, distance, horraire FROM Pharmacie ORDER BY distance ASC"
        )

    # ── Rendez-vous ──────────────────────────────────────────────────────────

    def find_medecin_by_name(self, name):
        # Nettoie "Dr." ou "Docteur" en préfixe
        import re
        name = re.sub(r"^(dr\.?\s*|docteur\s*)", "", name.strip(), flags=re.IGNORECASE).strip()
        p = f"%{name}%"
        return query_one(
            """SELECT id_medecin, prenom, nom, specialite
               FROM Medecin
               WHERE nom LIKE ?
                  OR prenom LIKE ?
                  OR (prenom || ' ' || nom) LIKE ?
                  OR (nom || ' ' || prenom) LIKE ?
               LIMIT 1""",
            (p, p, p, p),
        )

    def get_disponibilites(self, id_medecin):
        return query_all(
            "SELECT jour_semaine, heure_debut, heure_fin, duree_min"
            " FROM Disponibilites WHERE id_medecin = ? ORDER BY jour_semaine",
            (id_medecin,),
        )

    def get_reservations(self, id_medecin, date):
        rows = query_all(
            "SELECT heure FROM RendezVous WHERE id_medecin = ? AND date = ?",
            (id_medecin, date),
        )
        return {r["heure"] for r in rows}

    def get_available_slots(self, nom_medecin, nombre_jours=7, date=None):
        medecin = self.find_medecin_by_name(nom_medecin)
        if not medecin:
            return None, []

        dispos = self.get_disponibilites(medecin["id_medecin"])
        if not dispos:
            return medecin, []

        dispo_by_day = {d["jour_semaine"]: d for d in dispos}
        today = datetime.today().date()

        # Mode date précise : créneaux horaires pour ce jour
        if date:
            target = _parse_date(date)
            if target is None:
                return medecin, []
            jour_semaine = target.weekday()
            if jour_semaine not in dispo_by_day:
                return medecin, []
            d = dispo_by_day[jour_semaine]
            reservees = self.get_reservations(medecin["id_medecin"], str(target))
            slots = []
            current = datetime.strptime(d["heure_debut"], "%H:%M")
            end     = datetime.strptime(d["heure_fin"],   "%H:%M")
            while current < end:
                heure = current.strftime("%H:%M")
                if heure not in reservees:
                    slots.append({"date": str(target), "heure": heure})
                current += timedelta(minutes=d["duree_min"])
            return medecin, slots

        # Mode sans date : retourne les jours disponibles (pas tous les créneaux)
        available_dates = []
        for delta in range(1, nombre_jours + 1):
            day = today + timedelta(days=delta)
            jour_semaine = day.weekday()
            if jour_semaine not in dispo_by_day:
                continue
            d = dispo_by_day[jour_semaine]
            reservees = self.get_reservations(medecin["id_medecin"], str(day))
            # Compte les créneaux libres
            free = 0
            current = datetime.strptime(d["heure_debut"], "%H:%M")
            end     = datetime.strptime(d["heure_fin"],   "%H:%M")
            while current < end:
                if current.strftime("%H:%M") not in reservees:
                    free += 1
                current += timedelta(minutes=d["duree_min"])
            if free > 0:
                available_dates.append({"date": str(day), "creneaux_libres": free})

        return medecin, available_dates

    def book_appointment(self, nom_medecin, date, heure, nom_patient):
        medecin = self.find_medecin_by_name(nom_medecin)
        if not medecin:
            return False, "Médecin introuvable."

        try:
            with get_connection() as conn:
                conn.execute(
                    "INSERT INTO RendezVous (id_medecin, date, heure, nom_patient)"
                    " VALUES (?, ?, ?, ?)",
                    (medecin["id_medecin"], date, heure, nom_patient),
                )
                conn.commit()
            return True, "Réservé."
        except Exception:
            return False, "Ce créneau vient d'être pris par un autre patient."
