"""
Service de prise de rendez-vous conversationnel (multi-tours).

États stockés dans session['rdv'] :
  step        : etape courante (specialite | medecin | date | heure | nom | confirm)
  specialite  : spécialité demandée
  medecin_id  : id du médecin sélectionné
  nom_medecin : nom affiché du médecin
  date        : date souhaitée (texte libre)
  heure       : heure souhaitée
  nom         : nom du patient
  prenom      : prénom du patient
"""

import re
from repositories.rdv_repo import RDVRepository

SLOT_DURATION = 30  # minutes

from datetime import datetime, timedelta

MOIS_FR = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3,
    "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
    "aout": 8, "août": 8, "septembre": 9, "octobre": 10,
    "novembre": 11, "decembre": 12, "décembre": 12,
}

JOURS_FR = {
    "lundi": 0, "mardi": 1, "mercredi": 2,
    "jeudi": 3, "vendredi": 4, "samedi": 5, "dimanche": 6,
}


def _extract_date(text):
    """
    Extrait et normalise une date depuis un texte en français.
    Retourne une chaîne 'JJ/MM/AAAA' ou None.
    """
    t = text.lower().strip()
    today = datetime.today()

    # "demain"
    if "demain" in t:
        d = today + timedelta(days=1)
        return d.strftime("%d/%m/%Y")

    # "aujourd'hui"
    if "aujourd" in t:
        return today.strftime("%d/%m/%Y")

    # "JJ/MM" ou "JJ/MM/AAAA"
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
    if m:
        day  = int(m.group(1))
        mon  = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            d = datetime(year, mon, day)
            return d.strftime("%d/%m/%Y")
        except ValueError:
            pass

    # "15 avril" ou "mardi 15 avril" ou "le 15 avril 2026"
    m = re.search(
        r"\b(\d{1,2})\s+(" + "|".join(MOIS_FR.keys()) + r")\s*(\d{4})?\b",
        t
    )
    if m:
        day  = int(m.group(1))
        mon  = MOIS_FR[m.group(2)]
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            d = datetime(year, mon, day)
            return d.strftime("%d/%m/%Y")
        except ValueError:
            pass

    # "mardi" seul → prochain mardi
    for jour, weekday in JOURS_FR.items():
        if jour in t:
            days_ahead = (weekday - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            d = today + timedelta(days=days_ahead)
            return d.strftime("%d/%m/%Y")

    return None


def _parse_time(t):
    """'08:00' ou '8h30' → (heures, minutes)"""
    t = t.strip()
    m = re.match(r"(\d{1,2})[h:](\d{0,2})", t)
    if m:
        h = int(m.group(1))
        mn = int(m.group(2)) if m.group(2) else 0
        return h, mn
    return None


def _format_slot(h, mn):
    return "{}h{}".format(h, "{:02d}".format(mn)) if mn else "{}h".format(h)


def _generate_slots(horraire_str):
    """
    Génère les créneaux de 30 min à partir d'un horaire texte.
    Ex: '08:00-16:00' ou 'Lun-Ven 08:00-16:00'
    """
    if not horraire_str or "24h" in horraire_str:
        # Urgences 24h/24 → créneaux 8h-20h par défaut
        horraire_str = "08:00-20:00"

    m = re.search(r"(\d{1,2}[h:]\d{0,2})\s*[-–]\s*(\d{1,2}[h:]\d{0,2})", horraire_str)
    if not m:
        return []

    start = _parse_time(m.group(1))
    end   = _parse_time(m.group(2))
    if not start or not end:
        return []

    slots = []
    h, mn = start
    end_minutes = end[0] * 60 + end[1]

    while h * 60 + mn < end_minutes:
        slots.append(_format_slot(h, mn))
        mn += SLOT_DURATION
        if mn >= 60:
            h += 1
            mn -= 60
    return slots


def _normalize_heure(heure_str):
    """Normalise '14h00' → '14h', '9h30' → '9h30', '14:00' → '14h'"""
    parsed = _parse_time(heure_str)
    if parsed:
        return _format_slot(parsed[0], parsed[1])
    return heure_str

repo = RDVRepository()

# Mapping variantes → spécialité DB
SPECIALITE_MAP = {
    "cardio":       "Cardiologue",
    "cardiologie":  "Cardiologue",
    "cardiologue":  "Cardiologue",
    "radio":        "Radiologue",
    "radiologie":   "Radiologue",
    "radiologue":   "Radiologue",
    "pediatr":      "Pédiatre",
    "pédiatr":      "Pédiatre",
    "gyneco":       "Gynécologue",
    "gynécol":      "Gynécologue",
    "urgence":      "Urgentiste",
    "urgentiste":   "Urgentiste",
}


def _normalize_specialite(text):
    t = text.lower()
    for key, val in SPECIALITE_MAP.items():
        if key in t:
            return val
    return None


def _extract_heure(text):
    m = re.search(r"\b(\d{1,2})[h:]\s*(\d{0,2})\b", text.lower())
    if m:
        h = m.group(1)
        mn = m.group(2) or "00"
        return f"{h}h{mn}" if mn != "00" else f"{h}h"
    return None


def _extract_nom_prenom(text):
    """Tente d'extraire Prénom Nom depuis un texte libre."""
    # Supprimer mots parasites
    cleaned = re.sub(
        r"\b(je suis|je m'appelle|mon nom est|prénom|nom|c'est|bonjour)\b",
        "", text, flags=re.IGNORECASE
    ).strip()
    parts = cleaned.split()
    parts = [p.capitalize() for p in parts if p.isalpha()]
    if len(parts) >= 2:
        return parts[0], parts[1]      # prenom, nom
    if len(parts) == 1:
        return parts[0], ""
    return None, None


class RDVService:

    def handle(self, message, session):
        rdv = session.get("rdv", {})
        step = rdv.get("step")

        # ── Pas encore en cours : initialisation ─────────────────────────────
        if not step:
            return self._start(message, rdv, session)

        # ── En cours : traitement selon l'étape ──────────────────────────────
        if step == "need_specialite":
            return self._collect_specialite(message, rdv, session)
        if step == "need_medecin":
            return self._collect_medecin(message, rdv, session)
        if step == "need_date":
            return self._collect_date(message, rdv, session)
        if step == "need_heure":
            return self._collect_heure(message, rdv, session)
        if step == "need_nom":
            return self._collect_nom(message, rdv, session)

        return self._reply("Je ne comprends pas. Pouvez-vous recommencer ?", session, clear_rdv=True)

    # ── Initialisation ────────────────────────────────────────────────────────

    def _start(self, message, rdv, session):
        text = message.lower()
        rdv = {}

        # Chercher spécialité ou médecin dans le message initial
        specialite = _normalize_specialite(text)
        doctors = []

        if specialite:
            doctors = repo.find_doctors_by_specialite(specialite)
            rdv["specialite"] = specialite
        else:
            # Essayer par nom de médecin
            m = re.search(r"\b(?:docteur|dr\.?)\s+([a-zA-ZÀ-ÿ]+)", message, re.IGNORECASE)
            if m:
                doctors = repo.find_doctor_by_name(m.group(1))
                if doctors:
                    rdv["specialite"] = doctors[0]["specialite"]

        # Date
        date = _extract_date(message)
        if date:
            rdv["date"] = date

        # Heure
        heure = _extract_heure(message)
        if heure:
            rdv["heure"] = heure

        # Sélection médecin
        if doctors:
            rdv["medecin_id"]  = doctors[0]["id_medecin"]
            rdv["nom_medecin"] = doctors[0]["nom_medecin"]

        session["rdv"] = rdv
        return self._next_step(rdv, session)

    # ── Collecte des infos manquantes ─────────────────────────────────────────

    def _collect_specialite(self, message, rdv, session):
        specialite = _normalize_specialite(message)
        if not specialite:
            return self._reply(
                "Je n'ai pas reconnu la spécialité. Exemples : cardiologue, pédiatre, radiologue.",
                session
            )
        doctors = repo.find_doctors_by_specialite(specialite)
        if not doctors:
            return self._reply(
                f"Aucun médecin disponible en {specialite} pour le moment.",
                session, clear_rdv=True
            )
        rdv["specialite"]  = specialite
        rdv["medecin_id"]  = doctors[0]["id_medecin"]
        rdv["nom_medecin"] = doctors[0]["nom_medecin"]
        session["rdv"] = rdv
        return self._next_step(rdv, session)

    def _collect_medecin(self, message, rdv, session):
        # Même logique que collect_specialite pour l'instant
        return self._collect_specialite(message, rdv, session)

    def _collect_date(self, message, rdv, session):
        date = _extract_date(message)
        if date:
            rdv["date"] = date
            session["rdv"] = rdv
            return self._next_step(rdv, session)
        return self._reply(
            u"Quel jour souhaitez-vous le rendez-vous ?\n(ex: mardi, 15 avril, 15/04/2026)",
            session
        )

    def _collect_heure(self, message, rdv, session):
        heure = _extract_heure(message)
        if not heure:
            available = self._get_available_slots(rdv)
            slots_str = "  ".join(available) if available else ""
            msg = "Choisissez un créneau disponible :\n{}".format(slots_str) if slots_str else "À quelle heure ? (ex: 9h, 14h30)"
            return self._reply(msg, session)

        heure = _normalize_heure(heure)

        available     = self._get_available_slots(rdv)
        medecin_id    = rdv.get("medecin_id")
        date          = rdv.get("date")
        horraire      = repo.get_doctor_hours(medecin_id) if medecin_id else None
        all_slots     = _generate_slots(horraire)

        if not all_slots:
            # Pas de grille connue, on accepte directement
            rdv["heure"] = heure
            session["rdv"] = rdv
            return self._next_step(rdv, session)

        slots_str = "  ".join(available) if available else "aucun créneau disponible"

        if heure not in all_slots:
            return self._reply(
                u"Le créneau {} n'existe pas.\nCréneaux disponibles :\n{}".format(heure, slots_str),
                session
            )

        if heure not in available:
            return self._reply(
                u"Le créneau {} est déjà pris.\nCréneaux disponibles :\n{}".format(heure, slots_str),
                session
            )

        rdv["heure"] = heure
        session["rdv"] = rdv
        return self._next_step(rdv, session)

    def _collect_nom(self, message, rdv, session):
        prenom, nom = _extract_nom_prenom(message)
        if not prenom:
            return self._reply("Pouvez-vous me donner votre prénom et nom ?", session)
        rdv["prenom"] = prenom
        rdv["nom"]    = nom or prenom
        session["rdv"] = rdv
        return self._confirm(rdv, session)

    # ── Confirmation et insertion ─────────────────────────────────────────────

    def _confirm(self, rdv, session):
        try:
            patient_id = repo.get_or_create_patient(rdv["nom"], rdv["prenom"])
            repo.create_rdv(patient_id, rdv["medecin_id"], rdv["date"], rdv["heure"])
        except Exception as e:
            return self._reply("Une erreur est survenue lors de l'enregistrement. Veuillez réessayer.", session, clear_rdv=True)

        msg = (
            u"Rendez-vous confirmé !\n"
            u"Médecin : Dr. {}\n"
            u"Date    : {}\n"
            u"Heure   : {}\n"
            u"Patient : {} {}"
        ).format(
            rdv.get("nom_medecin", ""),
            rdv.get("date", ""),
            rdv.get("heure", ""),
            rdv.get("prenom", ""),
            rdv.get("nom", ""),
        )
        return self._reply(msg, session, clear_rdv=True)

    # ── Utilitaires ───────────────────────────────────────────────────────────

    def _next_step(self, rdv, session):
        if not rdv.get("medecin_id"):
            rdv["step"] = "need_specialite"
            session["rdv"] = rdv
            return self._reply("Quelle spécialité cherchez-vous ? (cardiologue, pédiatre, radiologue…)", session)

        if not rdv.get("date"):
            rdv["step"] = "need_date"
            session["rdv"] = rdv
            return self._reply(
                u"Pour un rendez-vous avec Dr. {} — quel jour vous convient ?".format(rdv["nom_medecin"]),
                session
            )

        if not rdv.get("heure"):
            rdv["step"] = "need_heure"
            session["rdv"] = rdv
            available = self._get_available_slots(rdv)
            if available:
                slots_str = "  ".join(available)
                msg = u"Dr. {} — {}.\nCréneaux disponibles :\n{}".format(
                    rdv["nom_medecin"], rdv["date"], slots_str
                )
            else:
                msg = u"Le {} avec Dr. {} — à quelle heure ?".format(
                    rdv["date"], rdv["nom_medecin"]
                )
            return self._reply(msg, session)

        if not rdv.get("prenom"):
            rdv["step"] = "need_nom"
            session["rdv"] = rdv
            return self._reply("Quel est votre prénom et nom ?", session)

        return self._confirm(rdv, session)

    def _get_available_slots(self, rdv):
        """Retourne les créneaux libres pour le médecin à la date donnée."""
        medecin_id = rdv.get("medecin_id")
        date       = rdv.get("date")
        if not medecin_id or not date:
            return []
        horraire  = repo.get_doctor_hours(medecin_id)
        all_slots = _generate_slots(horraire)
        booked    = repo.get_booked_slots(medecin_id, date)
        booked_norm = [_normalize_heure(h) for h in booked]
        return [s for s in all_slots if s not in booked_norm]

    def _reply(self, text, session, clear_rdv=False):
        if clear_rdv:
            session.pop("rdv", None)
        return {"response": text, "intent": "prise_rdv", "data": None}
