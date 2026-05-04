import json
from openai import OpenAI
from config import Config
from services.hospital_service import HospitalService
from repositories.hospital_repo import HospitalRepository
from repositories.conv_repo import ConversationRepository

_SYSTEM = (
    "Tu es Pepper, l'assistant d'accueil de l'hôpital. "
    "Tu réponds en français, de façon courte et naturelle, comme si tu parlais à un patient. "
    "Réponds en 1 à 3 phrases maximum. Pas d'emoji. Pas de mise en forme markdown. "
    "Pour toute question sur les services, médecins, horaires, contacts ou pharmacies, "
    "utilise TOUJOURS l'outil query_hospital avant de répondre. "
    "Pour les rendez-vous, suis ces étapes : "
    "1) Si le patient mentionne déjà un médecin, va directement à l'étape 3. "
    "Si le patient donne un service/spécialité sans médecin précis, appelle query_hospital "
    "intent=liste_medecins+nom_service pour proposer les médecins de ce service. "
    "Si le patient ne donne ni médecin ni service, demande-lui : "
    "'Connaissez-vous le nom du médecin, ou préférez-vous chercher par service ?' "
    "2) Attends que le patient choisisse un médecin parmi la liste proposée. "
    "3) Appelle get_available_slots SANS date pour obtenir les jours disponibles, "
    "puis demande au patient quel jour lui convient. "
    "4) Quand le patient choisit un jour, appelle get_available_slots AVEC la date "
    "et transmets le résultat tel quel au patient sans en ajouter d'autres. "
    "Si le patient veut un autre jour, rappelle get_available_slots avec la nouvelle date. "
    "5) Quand le patient choisit un créneau horaire précis, demande son nom complet. "
    "6) Appelle book_appointment avec toutes les informations. "
    "Pour les salutations et les au revoir, réponds directement sans outil."
)

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_hospital",
            "description": (
                "Interroge la base de données hospitalière. "
                "Pour liste_medecins, passer nom_service filtre les médecins de ce service/spécialité."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": [
                            "localisation_service", "horaires_service", "contact_service",
                            "localisation_medecin", "liste_services", "liste_medecins",
                            "information_pharmacie",
                        ],
                    },
                    "nom_service": {
                        "type": "string",
                        "description": "Service ou spécialité (ex: Cardiologie). Pour liste_medecins, filtre les médecins de ce service.",
                    },
                    "nom_medecin": {"type": "string"},
                },
                "required": ["intent"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": (
                "Sans 'date' : retourne les jours disponibles avec le nombre de créneaux libres. "
                "Avec 'date' (format YYYY-MM-DD) : retourne les créneaux horaires disponibles ce jour-là."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nom_medecin": {"type": "string"},
                    "nombre_jours": {
                        "type": "integer",
                        "description": "Nombre de jours à consulter si pas de date (défaut 7)",
                    },
                    "date": {
                        "type": "string",
                        "description": "Format YYYY-MM-DD. Si fourni, retourne les horaires de ce jour uniquement.",
                    },
                },
                "required": ["nom_medecin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Réserve un créneau pour un patient. Appelle get_available_slots d'abord pour vérifier la disponibilité.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nom_medecin":  {"type": "string"},
                    "date":         {"type": "string", "description": "Format YYYY-MM-DD"},
                    "heure":        {"type": "string", "description": "Format HH:MM"},
                    "nom_patient":  {"type": "string", "description": "Nom complet du patient"},
                },
                "required": ["nom_medecin", "date", "heure", "nom_patient"],
            },
        },
    },
]


def _rows_to_str(rows):
    if not rows:
        return "Aucune donnée trouvée dans la base de données."
    return "\n".join(
        ", ".join("{}: {}".format(k, v) for k, v in row.items() if v)
        for row in rows
    )


def _slots_to_str(medecin, slots):
    if medecin is None:
        return "Médecin introuvable dans la base de données."
    nom = "{} {}".format(medecin.get("prenom", ""), medecin.get("nom", "")).strip()
    if not slots:
        return "Aucune disponibilité pour {} dans les prochains jours.".format(nom)

    # Mode jours disponibles (clé "creneaux_libres")
    if "creneaux_libres" in slots[0]:
        lines = ["Jours disponibles pour {} :".format(nom)]
        for s in slots:
            lines.append("{} ({} créneaux libres)".format(s["date"], s["creneaux_libres"]))
        return "\n".join(lines)

    # Mode créneaux horaires d'une journée (clé "heure")
    date = slots[0]["date"]
    heures = [s["heure"] for s in slots]
    affiches = heures[:6]
    reste = len(heures) - len(affiches)
    ligne = "Créneaux disponibles le {} pour {} : {}".format(
        date, nom, ", ".join(affiches)
    )
    if reste > 0:
        ligne += " (et {} autres)".format(reste)
    ligne += "\nLequel vous convient ? Ou souhaitez-vous choisir un autre jour ?"
    return ligne


class DialogService:
    def __init__(self):
        self.client   = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.hospital = HospitalService()
        self.repo     = HospitalRepository()
        self.convs    = ConversationRepository()

    def _execute_tool(self, name, args):
        if name == "query_hospital":
            data = self.hospital.handle(
                args.get("intent", "inconnu"),
                {"nom_service": args.get("nom_service"), "nom_medecin": args.get("nom_medecin")},
            )
            return _rows_to_str(data)

        if name == "get_available_slots":
            medecin, slots = self.repo.get_available_slots(
                args["nom_medecin"], args.get("nombre_jours", 7), args.get("date"),
            )
            return _slots_to_str(medecin, slots)

        if name == "book_appointment":
            ok, msg = self.repo.book_appointment(
                args["nom_medecin"], args["date"], args["heure"], args["nom_patient"],
            )
            if ok:
                return "Rendez-vous confirmé le {} à {} pour {}.".format(
                    args["date"], args["heure"], args["nom_patient"]
                )
            return "Échec de la réservation : " + msg

        return "Outil inconnu."

    def handle_message(self, message, conversation_id):
        # Historique depuis la BDD
        history = self.convs.get_messages(conversation_id)

        oai_messages = [{"role": "system", "content": _SYSTEM}]
        for m in history[-10:]:
            oai_messages.append({
                "role": "assistant" if m["role"] == "bot" else "user",
                "content": m["content"],
            })
        oai_messages.append({"role": "user", "content": message})

        try:
            resp = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=oai_messages,
                tools=_TOOLS,
                tool_choice="auto",
                max_tokens=400,
                temperature=0.5,
            )
        except Exception as e:
            print("[OPENAI ERR]", e)
            return {"response": "Désolé, je suis temporairement indisponible."}

        response_message = resp.choices[0].message

        while response_message.tool_calls:
            oai_messages.append(response_message)
            for tool_call in response_message.tool_calls:
                args   = json.loads(tool_call.function.arguments)
                result = self._execute_tool(tool_call.function.name, args)
                oai_messages.append({
                    "role": "tool", "tool_call_id": tool_call.id, "content": result,
                })
            try:
                resp = self.client.chat.completions.create(
                    model=Config.OPENAI_MODEL,
                    messages=oai_messages,
                    tools=_TOOLS,
                    tool_choice="auto",
                    max_tokens=400,
                    temperature=0.5,
                )
            except Exception as e:
                print("[OPENAI ERR]", e)
                self.convs.append_message(conversation_id, "user", message)
                self.convs.append_message(conversation_id, "bot", "Désolé, je suis temporairement indisponible.")
                return {"response": "Désolé, je suis temporairement indisponible."}
            response_message = resp.choices[0].message

        bot_text = (response_message.content or "").strip()
        self.convs.append_message(conversation_id, "user", message)
        self.convs.append_message(conversation_id, "bot", bot_text)
        return {"response": bot_text}
