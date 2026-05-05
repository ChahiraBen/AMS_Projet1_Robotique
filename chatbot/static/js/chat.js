// ── SVG icons ─────────────────────────────────────────────────────────────────
var SVG_BOT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M12 2a2 2 0 0 1 2 2 2 2 0 0 1-2 2 2 2 0 0 1-2-2 2 2 0 0 1 2-2m-1 5h2v1h3a4 4 0 0 1 4 4v3a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-3a4 4 0 0 1 4-4h3V7M9 13a1.5 1.5 0 0 0-1.5 1.5A1.5 1.5 0 0 0 9 16a1.5 1.5 0 0 0 1.5-1.5A1.5 1.5 0 0 0 9 13m6 0a1.5 1.5 0 0 0-1.5 1.5A1.5 1.5 0 0 0 15 16a1.5 1.5 0 0 0 1.5-1.5A1.5 1.5 0 0 0 15 13z"/></svg>';
var SVG_USER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18"><path d="M12 12c2.7 0 5-2.3 5-5s-2.3-5-5-5-5 2.3-5 5 2.3 5 5 5zm0 2c-3.3 0-10 1.7-10 5v2h20v-2c0-3.3-6.7-5-10-5z"/></svg>';
var SVG_DEL  = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M6 19a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7H6v12zM8 9h8v10H8V9zm7.5-5-1-1h-5l-1 1H5v2h14V4z"/></svg>';

// ── Éléments DOM ──────────────────────────────────────────────────────────────
var form          = document.getElementById("chat-form");
var input         = document.getElementById("user-input");
var messages      = document.getElementById("messages");
var sendBtn       = document.getElementById("send-btn");
var micBtn        = document.getElementById("mic-btn");
var infoCard      = document.getElementById("info-card");
var cardTitle     = document.getElementById("card-title");
var cardBody      = document.getElementById("card-body");
var convList      = document.getElementById("conv-list");
var newChatBtn    = document.getElementById("new-chat-btn");
var sidebarToggle = document.getElementById("sidebar-toggle");
var sidebar       = document.getElementById("sidebar");

// ── État ──────────────────────────────────────────────────────────────────────
var currentConvId = null;
var isRecording   = false;

// ── Sidebar toggle ────────────────────────────────────────────────────────────
sidebarToggle.addEventListener("click", function() {
  sidebar.classList.toggle("collapsed");
});

// ── Conversations ─────────────────────────────────────────────────────────────
function loadConversations() {
  xhr("GET", "/conversations", null, function(data) {
    renderConvList(data);
    if (data.length === 0) {
      createConversation();
    } else if (!currentConvId) {
      switchConversation(data[0].id);
    }
  });
}

function renderConvList(convs) {
  convList.innerHTML = "";
  for (var i = 0; i < convs.length; i++) {
    (function(conv) {
      var item = document.createElement("div");
      item.className = "conv-item" + (conv.id === currentConvId ? " active" : "");
      item.dataset.id = conv.id;

      var title = document.createElement("span");
      title.className = "conv-title";
      title.textContent = conv.titre || "Nouvelle conversation";

      var del = document.createElement("button");
      del.className = "conv-delete";
      del.title = "Supprimer";
      del.innerHTML = SVG_DEL;
      del.addEventListener("click", function(e) {
        e.stopPropagation();
        deleteConversation(conv.id);
      });

      item.appendChild(title);
      item.appendChild(del);
      item.addEventListener("click", function() {
        switchConversation(conv.id);
      });
      convList.appendChild(item);
    })(convs[i]);
  }
}

function createConversation() {
  xhr("POST", "/conversations", {}, function(data) {
    currentConvId = data.id;
    loadConversations();
    clearMessages();
  });
}

function deleteConversation(convId) {
  xhr("DELETE", "/conversations/" + convId, null, function() {
    if (convId === currentConvId) currentConvId = null;
    loadConversations();
    if (!currentConvId) createConversation();
  });
}

function switchConversation(convId) {
  currentConvId = convId;
  clearMessages();
  xhr("GET", "/conversations/" + convId + "/messages", null, function(data) {
    var msgs = data.messages || [];
    if (msgs.length === 0) {
      addWelcome();
    } else {
      for (var i = 0; i < msgs.length; i++) {
        addMessage(msgs[i].content, msgs[i].role === "bot" ? "bot" : "user");
      }
    }
  });
  var items = convList.querySelectorAll(".conv-item");
  for (var i = 0; i < items.length; i++) {
    items[i].classList.toggle("active", items[i].dataset.id === convId);
  }
  hideCard();
}

function clearMessages() { messages.innerHTML = ""; }

function addWelcome() {
  addMessage("Bonjour ! Je suis Pepper, votre assistant d'accueil. Comment puis-je vous aider ?", "bot");
}

newChatBtn.addEventListener("click", createConversation);

// ── Envoi d'un message ────────────────────────────────────────────────────────
function sendMessage(text, source) {
  if (!currentConvId) return;
  source = source || "tablet";
  addMessage(text, "user");
  input.value = "";
  sendBtn.disabled = true;
  micBtn.disabled  = true;

  var typingEl = addTyping();

  xhr("POST", "/chatbot", { message: text, source: source, conversation_id: currentConvId }, function(data) {
    typingEl.remove();
    sendBtn.disabled = false;
    micBtn.disabled  = false;
    input.focus();
    addMessage(data.response || data.error || "Erreur inattendue.", "bot");
    loadConversations();
    hideCard();
  }, function() {
    typingEl.remove();
    sendBtn.disabled = false;
    micBtn.disabled  = false;
    addMessage("Erreur de connexion au serveur.", "bot");
  });
}

form.addEventListener("submit", function(e) {
  e.preventDefault();
  var text = input.value.trim();
  if (!text) return;
  sendMessage(text, "tablet");
});

// ── Micro ─────────────────────────────────────────────────────────────────────
function setMicUI(recording) {
  isRecording = recording;
  if (recording) {
    micBtn.classList.add("recording");
    micBtn.title      = "Arrêter l'enregistrement";
    input.placeholder = "Pepper écoute…";
  } else {
    micBtn.classList.remove("recording");
    micBtn.title      = "Parler";
    input.placeholder = "Posez votre question…";
  }
}

micBtn.addEventListener("click", function() {
  var endpoint = isRecording ? "/mic/stop" : "/mic/start";
  micBtn.disabled = true;
  var req = new XMLHttpRequest();
  req.open("POST", endpoint, true);
  req.onreadystatechange = function() {
    if (req.readyState !== 4) return;
    micBtn.disabled = false;
    setMicUI(!isRecording);
  };
  req.send();
});

// ── Polling mises à jour robot ────────────────────────────────────────────────
function pollUpdates() {
  var req = new XMLHttpRequest();
  req.open("GET", "/updates", true);
  req.onreadystatechange = function() {
    if (req.readyState !== 4 || req.status !== 200) return;
    try {
      var data = JSON.parse(req.responseText);
      var msgs = data.messages || [];
      for (var i = 0; i < msgs.length; i++) {
        addMessage(msgs[i].text, msgs[i].role);
      }
      if (msgs.length > 0) {
        setMicUI(false);
        hideCard();
        loadConversations();
      }
    } catch (e) {}
  };
  req.send();
}
setInterval(pollUpdates, 1000);

// ── Helpers DOM ───────────────────────────────────────────────────────────────
function scrollToBottom() {
  requestAnimationFrame(function() {
    messages.scrollTop = messages.scrollHeight;
  });
}

function makeAvatar(role) {
  var span = document.createElement("span");
  span.className = "avatar avatar-" + role;
  span.innerHTML = (role === "bot") ? SVG_BOT : SVG_USER;
  return span;
}

function addMessage(text, role) {
  var div    = document.createElement("div");
  div.className = "message " + role;
  var bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  if (role === "bot") {
    div.appendChild(makeAvatar("bot"));
    div.appendChild(bubble);
  } else {
    div.appendChild(bubble);
    div.appendChild(makeAvatar("user"));
  }
  messages.appendChild(div);
  scrollToBottom();
  return div;
}

function addTyping() {
  var div = document.createElement("div");
  div.className = "message bot typing";
  var bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  div.appendChild(makeAvatar("bot"));
  div.appendChild(bubble);
  messages.appendChild(div);
  scrollToBottom();
  return div;
}

// ── Helper XHR ────────────────────────────────────────────────────────────────
function xhr(method, url, data, onSuccess, onError) {
  var req = new XMLHttpRequest();
  req.open(method, url, true);
  req.setRequestHeader("Content-Type", "application/json");
  req.onreadystatechange = function() {
    if (req.readyState !== 4) return;
    if (req.status >= 200 && req.status < 300) {
      try { onSuccess(JSON.parse(req.responseText)); } catch(e) { if (onError) onError(); }
    } else {
      if (onError) onError();
    }
  };
  req.send(data ? JSON.stringify(data) : null);
}

// ── Info card ─────────────────────────────────────────────────────────────────
var SERVICE_PLANS = {
  "urgences":   "/static/img/plans/plan_urgences.svg",
  "radiologie": "/static/img/plans/plan_radiologie.svg",
  "cardiologie":"/static/img/plans/plan_cardiologie.svg",
  "pediatrie":  "/static/img/plans/plan_pediatrie.svg",
  "maternite":  "/static/img/plans/plan_maternite.svg"
};

function showCard(intent, rows) {
  infoCard.className = infoCard.className.replace(/\bhidden\b/g, "").trim();
  cardBody.innerHTML = "";
  var titles = {
    localisation_service:  "Localisation du service",
    horaires_service:      "Horaires du service",
    localisation_medecin:  "Médecin",
    contact_service:       "Contact",
    information_pharmacie: "Pharmacies proches"
  };
  cardTitle.textContent = titles[intent] || "Informations";
  for (var i = 0; i < rows.length; i++) {
    var row   = rows[i];
    var entry = document.createElement("div");
    entry.className = "card-entry";
    if (intent === "localisation_service" || intent === "horaires_service" || intent === "contact_service") {
      entry.appendChild(makeRow("Service", row.nom_service));
      if (row.nom_hopital)  entry.appendChild(makeRow("Hôpital",      row.nom_hopital));
      if (row.localisation) entry.appendChild(makeRow("Localisation", row.localisation));
      if (row.horaire)      entry.appendChild(makeRow("Horaires",     row.horaire));
      if (row.num_tel)      entry.appendChild(makeRow("Téléphone",    row.num_tel));
      if (row.adresse)      entry.appendChild(makeRow("Adresse",      row.adresse));
      if (intent === "localisation_service" && row.nom_service) {
        var key = row.nom_service.toLowerCase()
          .replace(/[éèê]/g,"e").replace(/[â]/g,"a").replace(/[î]/g,"i");
        if (SERVICE_PLANS[key]) {
          var img = document.createElement("img");
          img.src = SERVICE_PLANS[key];
          img.style.cssText = "width:100%;border-radius:8px;margin-top:10px";
          entry.appendChild(img);
        }
      }
    } else if (intent === "localisation_medecin") {
      entry.appendChild(makeRow("Médecin",   row.nom_medecin));
      if (row.specialite)   entry.appendChild(makeRow("Spécialité",  row.specialite));
      if (row.localisation) entry.appendChild(makeRow("Bureau",      row.localisation));
      if (row.horaire)      entry.appendChild(makeRow("Horaires",    row.horaire));
    } else if (intent === "information_pharmacie") {
      entry.appendChild(makeRow("Pharmacie", row.nom));
      if (row.adresse)  entry.appendChild(makeRow("Adresse",  row.adresse));
      if (row.distance) entry.appendChild(makeRow("Distance", row.distance + " km"));
      if (row.horaire)  entry.appendChild(makeRow("Horaires", row.horaire));
    }
    cardBody.appendChild(entry);
  }
}

function makeRow(label, value) {
  var div = document.createElement("div"); div.className = "card-row";
  var lbl = document.createElement("span"); lbl.className = "card-label"; lbl.textContent = label;
  var val = document.createElement("span"); val.className = "card-value"; val.textContent = value;
  div.appendChild(lbl); div.appendChild(val);
  return div;
}

function hideCard() {
  if (infoCard.className.indexOf("hidden") === -1) infoCard.className += " hidden";
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadConversations();
