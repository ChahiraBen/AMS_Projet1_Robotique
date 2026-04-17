from repositories.db import query_one, query_all

class HospitalRepository:
    def find_service_location(self, service_name):
        sql = """
        SELECT s.nom_service,
               s.etage,
               CASE WHEN s.etage = 0 THEN 'Rez-de-chaussee'
                    ELSE 'Etage ' || s.etage END AS localisation,
               NULL AS nom_hopital
        FROM Service s
        WHERE s.nom_service LIKE ?
        """
        return query_all(sql, (f"%{service_name}%",))

    def find_doctor_location(self, doctor_name):
        sql = """
        SELECT (m.prenom || ' ' || m.nom) AS nom_medecin,
               m.specialite,
               s.nom_service              AS localisation,
               m.horraire                 AS horaire,
               NULL                       AS nom_hopital
        FROM Medecin m
        LEFT JOIN Service s ON m.id_service = s.id_service
        WHERE m.nom LIKE ? OR m.prenom LIKE ?
        """
        return query_all(sql, (f"%{doctor_name}%", f"%{doctor_name}%"))

    def find_service_hours(self, service_name):
        sql = """
        SELECT s.nom_service,
               s.horraire AS horaire,
               NULL        AS nom_hopital
        FROM Service s
        WHERE s.nom_service LIKE ?
        """
        return query_all(sql, (f"%{service_name}%",))

    def find_service_contact(self, service_name):
        sql = """
        SELECT s.nom_service,
               h.nom      AS nom_hopital,
               h.num_tel,
               h.adresse
        FROM Service s, Hopital h
        WHERE s.nom_service LIKE ?
        LIMIT 1
        """
        return query_all(sql, (f"%{service_name}%",))

    def find_all_services(self):
        sql = """
        SELECT nom_service,
               CASE WHEN etage = 0 THEN 'Rez-de-chaussee'
                    ELSE 'Etage ' || etage END AS localisation
        FROM Service
        ORDER BY nom_service
        """
        return query_all(sql)

    def find_all_doctors(self):
        sql = """
        SELECT (m.prenom || ' ' || m.nom) AS nom_medecin,
               m.specialite,
               s.nom_service              AS localisation
        FROM Medecin m
        LEFT JOIN Service s ON m.id_service = s.id_service
        ORDER BY m.nom
        """
        return query_all(sql)

    def find_nearest_pharmacies(self):
        sql = """
        SELECT nom, adresse, distance,
               telephone AS num_tel,
               horraire  AS horaire
        FROM Pharmacie
        ORDER BY distance ASC
        """
        return query_all(sql)
