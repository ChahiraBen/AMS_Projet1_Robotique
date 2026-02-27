from repositories.db import query_one, query_all

class HospitalRepository:
    def find_service_location(self, service_name):
        sql = """
        SELECT s.nom_service, s.localisation, h.nom_hopital
        FROM Service s
        JOIN Hopital h ON s.id_hopital = h.id_hopital
        WHERE s.nom_service LIKE ?
        """
        return query_all(sql, (f"%{service_name}%",))

    def find_doctor_location(self, doctor_name):
        sql = """
        SELECT m.nom_medecin, m.specialite, m.localisation, h.nom_hopital
        FROM Medecin m
        JOIN Hopital h ON m.id_hopital = h.id_hopital
        WHERE m.nom_medecin LIKE ?
        """
        return query_all(sql, (f"%{doctor_name}%",))

    def find_service_hours(self, service_name):
        sql = """
        SELECT s.nom_service, s.horaire, h.nom_hopital
        FROM Service s
        JOIN Hopital h ON s.id_hopital = h.id_hopital
        WHERE s.nom_service LIKE ?
        """
        return query_all(sql, (f"%{service_name}%",))

    def find_service_contact(self, service_name):
        sql = """
        SELECT s.nom_service, h.nom_hopital, h.num_tel, h.adresse
        FROM Service s
        JOIN Hopital h ON s.id_hopital = h.id_hopital
        WHERE s.nom_service LIKE ?
        """
        return query_all(sql, (f"%{service_name}%",))

    def find_nearest_pharmacies(self):
        sql = """
        SELECT nom, adresse, distance, horaire
        FROM Pharmacie
        ORDER BY distance ASC
        """
        return query_all(sql)
