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
