// ── Gestion de session ──────────────────────────────────────────────────────
var INACTIVITY_SECONDS = 60;
var inactivityTimer = null;
var countdownTimer  = null;
var secondsLeft     = INACTIVITY_SECONDS;
var sessionTimerEl  = document.getElementById("session-timer");

function resetInactivityTimer() {
  secondsLeft = INACTIVITY_SECONDS;
  clearTimeout(inactivityTimer);
  clearInterval(countdownTimer);
  sessionTimerEl.textContent = "";

  countdownTimer = setInterval(function() {
    secondsLeft--;
    if (secondsLeft <= 15) {
      sessionTimerEl.textContent = "Session expire dans " + secondsLeft + "s";
    }
    if (secondsLeft <= 0) {
      clearInterval(countdownTimer);
      resetSession();
    }
  }, 1000);
}

function resetSession() {
  clearTimeout(inactivityTimer);
  clearInterval(countdownTimer);
  sessionTimerEl.textContent = "";

  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/reset", true);
  xhr.onreadystatechange = function() {
    if (xhr.readyState !== 4) return;
    messages.innerHTML = '<div class="message bot"><div class="bubble">Bonjour, comment puis-je vous aider ?</div></div>';
    hideCard();
    input.value = "";
    input.focus();
    resetInactivityTimer();
  };
  xhr.send();
}

// Démarrer le timer dès le chargement
resetInactivityTimer();

// ── Chat ────────────────────────────────────────────────────────────────────
var form      = document.getElementById("chat-form");
var input     = document.getElementById("user-input");
var messages  = document.getElementById("messages");
var sendBtn   = document.getElementById("send-btn");
var infoCard  = document.getElementById("info-card");
var cardTitle = document.getElementById("card-title");
var cardBody  = document.getElementById("card-body");

// Quick buttons
var quickBtns = document.querySelectorAll(".quick-btn");
for (var i = 0; i < quickBtns.length; i++) {
  (function(btn) {
    btn.addEventListener("click", function() {
      input.value = btn.getAttribute("data-msg");
      form.dispatchEvent(new Event("submit"));
    });
  })(quickBtns[i]);
}

form.addEventListener("submit", function(e) {
  e.preventDefault();
  var text = input.value.trim();
  if (!text) return;

  resetInactivityTimer();
  addMessage(text, "user");
  input.value = "";
  sendBtn.disabled = true;

  var typingEl = addTyping();

  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/chatbot", true);
  xhr.setRequestHeader("Content-Type", "application/json");

  xhr.onreadystatechange = function() {
    if (xhr.readyState !== 4) return;
    typingEl.remove();
    sendBtn.disabled = false;
    input.focus();
    if (xhr.status === 200) {
      try {
        var data = JSON.parse(xhr.responseText);
        addMessage(data.response || data.error || "Erreur inattendue.", "bot");
        if (data.data && data.data.length > 0) {
          showCard(data.intent, data.data);
        } else {
          hideCard();
        }
      } catch (err) {
        addMessage("Erreur de lecture de la réponse.", "bot");
      }
    } else {
      addMessage("Erreur de connexion au serveur.", "bot");
    }
  };

  xhr.onerror = function() {
    typingEl.remove();
    sendBtn.disabled = false;
    addMessage("Erreur de connexion au serveur.", "bot");
  };

  xhr.send(JSON.stringify({ message: text }));
});

function addMessage(text, role) {
  var div = document.createElement("div");
  div.className = "message " + role;
  var bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  div.appendChild(bubble);
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function addTyping() {
  var div = document.createElement("div");
  div.className = "message bot typing";
  div.innerHTML = '<div class="bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>';
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

var SERVICE_PLANS = {
  "urgences":   "/static/img/plans/plan_urgences.svg",
  "radiologie": "/static/img/plans/plan_radiologie.svg",
  "cardiologie":"/static/img/plans/plan_cardiologie.svg",
  "pédiatrie":  "/static/img/plans/plan_pediatrie.svg",
  "pediatrie":  "/static/img/plans/plan_pediatrie.svg",
  "maternité":  "/static/img/plans/plan_maternite.svg",
  "maternite":  "/static/img/plans/plan_maternite.svg"
};

function showCard(intent, rows) {
  infoCard.className = infoCard.className.replace(" hidden", "").replace("hidden", "");
  cardBody.innerHTML = "";

  var titles = {
    localisation_service:  "Localisation du service",
    horaires_service:      "Horaires du service",
    localisation_medecin:  "Medecin",
    contact_service:       "Contact",
    information_pharmacie: "Pharmacies proches"
  };
  cardTitle.textContent = titles[intent] || "Informations";

  for (var i = 0; i < rows.length; i++) {
    var row = rows[i];
    var entry = document.createElement("div");
    entry.className = "card-entry";

    if (intent === "localisation_service" || intent === "horaires_service" || intent === "contact_service") {
      entry.appendChild(makeRow("Service", row.nom_service));
      if (row.nom_hopital)  entry.appendChild(makeRow("Hopital",      row.nom_hopital));
      if (row.localisation) entry.appendChild(makeRow("Localisation", row.localisation));
      if (row.horaire)      entry.appendChild(makeRow("Horaires",     row.horaire));
      if (row.num_tel)      entry.appendChild(makeRow("Telephone",    row.num_tel));
      if (row.adresse)      entry.appendChild(makeRow("Adresse",      row.adresse));

      // Plan visuel
      if (intent === "localisation_service" && row.nom_service) {
        var key = row.nom_service.toLowerCase()
          .replace("é","e").replace("è","e").replace("ê","e")
          .replace("â","a").replace("î","i");
        var planUrl = SERVICE_PLANS[key];
        if (planUrl) {
          var planDiv = document.createElement("div");
          planDiv.style.marginTop = "10px";
          var img = document.createElement("img");
          img.src = planUrl;
          img.style.width = "100%";
          img.style.borderRadius = "8px";
          img.style.border = "1px solid #e0e0e0";
          planDiv.appendChild(img);
          entry.appendChild(planDiv);
        }
      }
    } else if (intent === "localisation_medecin") {
      entry.appendChild(makeRow("Medecin",    row.nom_medecin));
      if (row.specialite)   entry.appendChild(makeRow("Specialite",  row.specialite));
      if (row.nom_hopital)  entry.appendChild(makeRow("Hopital",     row.nom_hopital));
      if (row.localisation) entry.appendChild(makeRow("Bureau",      row.localisation));
      if (row.horaire)      entry.appendChild(makeRow("Horaires",    row.horaire));
    } else if (intent === "information_pharmacie") {
      entry.appendChild(makeRow("Pharmacie",  row.nom));
      if (row.adresse)      entry.appendChild(makeRow("Adresse",     row.adresse));
      if (row.distance)     entry.appendChild(makeRow("Distance",    row.distance + " km"));
      if (row.horaire)      entry.appendChild(makeRow("Horaires",    row.horaire));
    }

    cardBody.appendChild(entry);
  }
}

function makeRow(label, value) {
  var div = document.createElement("div");
  div.className = "card-row";
  var lbl = document.createElement("span");
  lbl.className = "card-label";
  lbl.textContent = label;
  var val = document.createElement("span");
  val.className = "card-value";
  val.textContent = value;
  div.appendChild(lbl);
  div.appendChild(val);
  return div;
}

function hideCard() {
  if (infoCard.className.indexOf("hidden") === -1) {
    infoCard.className += " hidden";
  }
}
