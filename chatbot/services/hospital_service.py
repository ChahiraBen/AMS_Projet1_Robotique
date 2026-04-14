from repositories.hospital_repo import HospitalRepository

class HospitalService:
    def __init__(self):
        self.repo = HospitalRepository()

    def handle(self, intent, entities):
        if intent == "salutation":
            return {"need_clarification": False, "text": "Bonjour, comment puis-je vous aider ?", "data": None}

        if intent == "au_revoir":
            return {"need_clarification": False, "text": "Au revoir, bonne journée.", "data": None}

        if intent == "localisation_service":
            service = entities.get("nom_service")
            if not service:
                return {"need_clarification": True, "text": "Quel service cherchez-vous ?"}
            rows = self.repo.find_service_location(service)
            if not rows:
                return {"need_clarification": False, "text": "Je ne dispose pas de cette information.", "data": None}
            return {"need_clarification": False, "data": rows, "text": None}

        if intent == "horaires_service":
            service = entities.get("nom_service")
            if not service:
                return {"need_clarification": True, "text": "De quel service souhaitez-vous connaître les horaires ?"}
            rows = self.repo.find_service_hours(service)
            if not rows:
                return {"need_clarification": False, "text": "Je ne dispose pas de cette information.", "data": None}
            return {"need_clarification": False, "data": rows, "text": None}

        if intent == "localisation_medecin":
            med = entities.get("nom_medecin")
            if not med:
                return {"need_clarification": True, "text": "Quel est le nom du médecin ?"}
            rows = self.repo.find_doctor_location(med)
            if not rows:
                return {"need_clarification": False, "text": "Je ne dispose pas de cette information.", "data": None}
            if len(rows) > 1:
                return {
                    "need_clarification": True,
                    "text": "J'ai trouvé plusieurs médecins. Pouvez-vous préciser le nom complet ou le service ?",
                }
            return {"need_clarification": False, "data": rows, "text": None}

        if intent == "contact_service":
            service = entities.get("nom_service")
            if not service:
                return {"need_clarification": True, "text": "Pour quel service souhaitez-vous le contact ?"}
            rows = self.repo.find_service_contact(service)
            if not rows:
                return {"need_clarification": False, "text": "Je ne dispose pas de cette information.", "data": None}
            return {"need_clarification": False, "data": rows, "text": None}

        if intent == "liste_services":
            rows = self.repo.find_all_services()
            if not rows:
                return {"need_clarification": False, "text": "Je ne dispose pas de cette information.", "data": None}
            return {"need_clarification": False, "data": rows, "text": None}

        if intent == "liste_medecins":
            rows = self.repo.find_all_doctors()
            if not rows:
                return {"need_clarification": False, "text": "Je ne dispose pas de cette information.", "data": None}
            return {"need_clarification": False, "data": rows, "text": None}

        if intent == "information_pharmacie":
            rows = self.repo.find_nearest_pharmacies()
            if not rows:
                return {"need_clarification": False, "text": "Je ne dispose pas de cette information.", "data": None}
            return {"need_clarification": False, "data": rows, "text": None}

        return {"need_clarification": False, "text": "Je n'ai pas compris votre demande.", "data": None}
