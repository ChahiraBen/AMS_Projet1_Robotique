from flask import Flask, request, jsonify

from config import MAX_TURNS
from dialog.context import ContextStore
from services.nlu import extract_intent_entities
from logic.router import run_intent, clarification_text
from services.nlg import generate_answer

app = Flask(__name__)
ctx = ContextStore(max_turns=MAX_TURNS)

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

@app.post("/chat")
def chat():
    payload = request.get_json(force=True)
    session_id = payload.get("session_id", "default")
    user_text = (payload.get("text") or "").strip()

    if not user_text:
        return jsonify({"error": "Missing 'text'"}), 400

    history = ctx.get_history(session_id)
    state = ctx.get_state(session_id)

    # 1) NLU
    nlu = extract_intent_entities(user_text, history)
    intent = nlu["intent"]
    entities = nlu["entities"]

    # 2) inject contexte si utile (multi-tours)
    if not entities.get("nom_service") and state.get("last_service") and intent in ("localisation_service", "horaires_service", "contact_service"):
        entities["nom_service"] = state["last_service"]
    if not entities.get("nom_medecin") and state.get("last_medecin") and intent == "localisation_medecin":
        entities["nom_medecin"] = state["last_medecin"]
    if not entities.get("specialite") and state.get("last_specialite") and intent == "localisation_medecin":
        entities["specialite"] = state["last_specialite"]

    # 3) SQL / logique
    data, need = run_intent(intent, entities)

    # clarification si entité manquante
    if need:
        answer = clarification_text(need)
        ctx.append_turn(session_id, user_text, answer)
        return jsonify({
            "session_id": session_id,
            "intent": intent,
            "entities": entities,
            "data": None,
            "answer": answer,
            "display": {"title": "Précision", "lines": [answer]},
            "debug": {"nlu_raw": nlu["raw"]}
        })

    # intent salutation (réponse statique)
    if isinstance(data, dict) and data.get("type") == "static":
        answer = data["text"]
        ctx.append_turn(session_id, user_text, answer)
        return jsonify({
            "session_id": session_id,
            "intent": intent,
            "entities": entities,
            "data": None,
            "answer": answer,
            "display": {"title": "Bonjour", "lines": []},
            "debug": {"nlu_raw": nlu["raw"]}
        })

    # 4) update contexte (si on a des infos)
    if entities.get("nom_service"):
        ctx.set_last(session_id, nom_service=entities["nom_service"])
    if entities.get("nom_medecin"):
        ctx.set_last(session_id, nom_medecin=entities["nom_medecin"])
    if entities.get("specialite"):
        ctx.set_last(session_id, specialite=entities["specialite"])

    # 5) NLG
    answer = generate_answer(user_text, history, data)

    # display simple (tablette)
    lines = []
    if isinstance(data, dict) and data:
        for k, v in data.items():
            lines.append(f"{k} : {v}")
    elif isinstance(data, list) and data:
        # pharmacies
        for item in data[:3]:
            if "nom" in item and "distance" in item:
                lines.append(f"{item['nom']} — {item['distance']} km")
            else:
                lines.append(str(item))
    else:
        lines.append(answer)

    ctx.append_turn(session_id, user_text, answer)

    return jsonify({
        "session_id": session_id,
        "intent": intent,
        "entities": entities,
        "data": data,
        "answer": answer,
        "display": {"title": "Réponse", "lines": lines[:6]},
        "debug": {"nlu_raw": nlu["raw"]}
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
