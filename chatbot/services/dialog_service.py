from utils.session_store import get_history, append_history, get_context, set_context
from services.nlu_service import NLUService
from services.hospital_service import HospitalService
from services.response_service import ResponseService

class DialogService:
    def __init__(self):
        self.nlu = NLUService()
        self.hospital = HospitalService()
        self.responder = ResponseService()

    def handle_message(self, message, session):
        history = get_history(session)
        context = get_context(session)

        nlu = self.nlu.extract(message, history)
        intent = nlu.get("intent", "inconnu")
        entities = nlu.get("entities", {}) or {}

        if not entities.get("nom_service") and context.get("last_service"):
            entities["nom_service"] = context.get("last_service")
        if not entities.get("nom_medecin") and context.get("last_medecin"):
            entities["nom_medecin"] = context.get("last_medecin")

        if intent == "inconnu" and entities.get("nom_service"):
            intent = "localisation_service"

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
