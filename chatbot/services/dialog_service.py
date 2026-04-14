from utils.session_store import get_history, append_history, get_context, set_context
from services.nlu_service import NLUService
from services.hospital_service import HospitalService
from services.response_service import ResponseService
from services.rdv_service import RDVService

class DialogService:
    def __init__(self):
        self.nlu = NLUService()
        self.hospital = HospitalService()
        self.responder = ResponseService()
        self.rdv = RDVService()

    def handle_message(self, message, session):
        history = get_history(session)
        context = get_context(session)

        # Si une prise de RDV est en cours, continuer ce dialogue en priorité
        if session.get("rdv"):
            result = self.rdv.handle(message, session)
            append_history(session, message, result["response"])
            return result

        nlu = self.nlu.extract(message, history)
        intent = nlu.get("intent", "inconnu")
        entities = nlu.get("entities", {}) or {}

        # Remplissage multi-tours : si l'entité manque, reprendre depuis le contexte.
        if not entities.get("nom_service") and context.get("last_service"):
            entities["nom_service"] = context.get("last_service")
        if not entities.get("nom_medecin") and context.get("last_medecin"):
            entities["nom_medecin"] = context.get("last_medecin")

        # Cas spécifique : "et à quel étage ?" après une demande de localisation de service.
        if intent == "inconnu" and entities.get("nom_service"):
            intent = "localisation_service"

        # Prise de RDV
        if intent == "prise_rdv":
            result = self.rdv.handle(message, session)
            append_history(session, message, result["response"])
            return result

        # logique hôpital
        hospital_result = self.hospital.handle(intent, entities)

        if hospital_result.get("need_clarification"):
            bot_text = hospital_result["text"]
            append_history(session, message, bot_text)
            return {"response": bot_text, "intent": intent, "entities": entities}

        if hospital_result.get("text"):
            bot_text = hospital_result["text"]
            append_history(session, message, bot_text)
            set_context(
                session,
                last_intent=intent,
                last_service=entities.get("nom_service"),
                last_medecin=entities.get("nom_medecin"),
            )
            return {"response": bot_text, "intent": intent, "entities": entities, "data": hospital_result.get("data")}

        data = hospital_result.get("data")

        # Génération réponse finale
        bot_text = self.responder.generate(message, history, data, intent)
        append_history(session, message, bot_text)
        set_context(
            session,
            last_intent=intent,
            last_service=entities.get("nom_service"),
            last_medecin=entities.get("nom_medecin"),
        )

        return {"response": bot_text, "intent": intent, "entities": entities, "data": data}
