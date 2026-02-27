def get_history(session):
    return session.get("history", [])

def append_history(session, user_text, bot_text):
    history = session.get("history", [])
    history.append({"user": user_text, "bot": bot_text})
    session["history"] = history[-10:]  # garder 10 tours

def get_context(session):
    return session.get("context", {})

def set_context(session, **kwargs):
    ctx = session.get("context", {})
    ctx.update(kwargs)
    session["context"] = ctx