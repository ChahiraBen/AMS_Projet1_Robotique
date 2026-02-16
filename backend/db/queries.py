SQL_LOCALISATION_SERVICE = """
SELECT etage, nom_service
FROM Service
WHERE nom_service = :nom_service
"""

SQL_HORAIRES_SERVICE = """
SELECT horaire
FROM Service
WHERE nom_service = :nom_service
"""

SQL_LOCALISATION_MEDECIN = """
SELECT Medecin.nom, Service.nom_service, Service.etage
FROM Medecin
JOIN Service ON Medecin.id_service = Service.id_service
WHERE Medecin.nom = :nom_medecin
   OR Service.nom_service = :specialite
"""

SQL_CONTACT_SERVICE = """
SELECT Hopital.num_tel
FROM Hopital
JOIN Service ON Hopital.id_hopital = Service.id_hopital
WHERE Service.nom_service = :nom_service
"""

SQL_INFO_PHARMACIE = """
SELECT nom, adresse, horaire, distance
FROM Pharmacie
ORDER BY distance ASC
"""
