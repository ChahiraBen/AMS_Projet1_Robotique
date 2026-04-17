from google import genai
from config import Config
from utils.prompts import ANSWER_PROMPT


# ---------------------------------------------------------------------------
# Génération de réponse de secours (sans LLM)
# ---------------------------------------------------------------------------

def _format_fallback(data: list, intent: str) -> str:
    if not data:
        return "Je ne dispose pas de cette information."

    parts = []
    for row in data:
        if intent == "localisation_service":
            svc  = row.get("nom_service", "")
            loc  = row.get("localisation", "")
            hop  = row.get("nom_hopital", "")
            line = f"Le service {svc} se trouve {loc}"
            if hop:
                line += f" ({hop})"
            parts.append(line + ".")

        elif intent == "horaires_service":
            svc = row.get("nom_service", "")
            hor = row.get("horaire", "")
            hop = row.get("nom_hopital", "")
            line = f"Le service {svc} est ouvert : {hor}"
            if hop:
                line += f" ({hop})"
            parts.append(line + ".")

        elif intent == "localisation_medecin":
            nom  = row.get("nom_medecin", "")
            spec = row.get("specialite", "")
            loc  = row.get("localisation", "")
            hor  = row.get("horaire", "")
            line = f"{nom}"
            if spec:
                line += f", spécialiste en {spec}"
            if loc:
                line += f", se trouve au {loc}"
            if hor:
                line += f". Consultations : {hor}"
            parts.append(line + ".")

        elif intent == "contact_service":
            svc = row.get("nom_service", "")
            tel = row.get("num_tel", "")
            adr = row.get("adresse", "")
            line = f"Pour le service {svc}"
            if tel:
                line += f", téléphone : {tel}"
            if adr:
                line += f", adresse : {adr}"
            parts.append(line + ".")

        elif intent == "information_pharmacie":
            nom = row.get("nom", "")
            adr = row.get("adresse", "")
            dst = row.get("distance", "")
            hor = row.get("horaire", "")
            line = f"{nom} ({dst} km) — {adr}. Horaires : {hor}"
            parts.append(line + ".")

        elif intent == "liste_services":
            svc = row.get("nom_service", "")
            loc = row.get("localisation", "")
            parts.append(f"{svc} — {loc}")

        elif intent == "liste_medecins":
            nom  = row.get("nom_medecin", "")
            spec = row.get("specialite", "")
            line = nom
            if spec:
                line += f" ({spec})"
            parts.append(line)

        else:
            # Réponse générique
            vals = [str(v) for v in row.values() if v]
            parts.append(", ".join(vals) + ".")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Service principal
# ---------------------------------------------------------------------------

class ResponseService:
    def __init__(self):
        self._gemini_available = bool(Config.GEMINI_API_KEY)
        if self._gemini_available:
            try:
                self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
            except Exception:
                self._gemini_available = False

    def generate(self, question: str, history, data, intent: str = "") -> str:
        if self._gemini_available:
            result = self._generate_gemini(question, history, data)
            if result and result != "Je ne dispose pas de cette information.":
                return result

        return _format_fallback(data if isinstance(data, list) else [], intent)

    def _generate_gemini(self, question: str, history, data) -> str:
        prompt = ANSWER_PROMPT.format(question=question, history=history, data=data)
        try:
            resp = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
            )
            text = (resp.text or "").strip()
            return text or "Je ne dispose pas de cette information."
        except Exception:
            self._gemini_available = False
            return "Je ne dispose pas de cette information."
