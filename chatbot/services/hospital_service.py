from repositories.hospital_repo import HospitalRepository


class HospitalService:
    def __init__(self):
        self.repo = HospitalRepository()

    def handle(self, intent, entities):
        nom_service = entities.get("nom_service")
        nom_medecin = entities.get("nom_medecin")

        if intent == "localisation_service":
            return self.repo.find_service_location(nom_service) if nom_service else []
        if intent == "horaires_service":
            return self.repo.find_service_hours(nom_service) if nom_service else []
        if intent == "contact_service":
            return self.repo.find_service_contact(nom_service) if nom_service else []
        if intent == "localisation_medecin":
            return self.repo.find_doctor_location(nom_medecin) if nom_medecin else []
        if intent == "liste_services":
            return self.repo.find_all_services()
        if intent == "liste_medecins":
            return self.repo.find_all_doctors(nom_service)
        if intent == "information_pharmacie":
            return self.repo.find_nearest_pharmacies()
        return []
