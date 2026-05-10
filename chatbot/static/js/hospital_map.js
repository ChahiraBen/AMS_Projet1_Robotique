// ── Polyfills navigateurs anciens ────────────────────────────────────────────
var _raf = window.requestAnimationFrame
        || window.webkitRequestAnimationFrame
        || window.mozRequestAnimationFrame
        || function(cb) { return setTimeout(cb, 16); };
var _caf = window.cancelAnimationFrame
        || window.webkitCancelAnimationFrame
        || function(id) { clearTimeout(id); };

// ── Carte et navigation hospitalière ─────────────────────────────────────────
var HospitalMap = (function () {

  var CW = 270, CH = 220;

  // Bâtiments sous forme de tableau (compatible tous navigateurs)
  var BUILDINGS = [
    { key:"urgences",    x:5,   y:10,  w:65, h:38, label:"Urgences",    color:"#c0392b" },
    { key:"accueil",     x:102, y:10,  w:66, h:38, label:"Accueil",     color:"#1a6fc4" },
    { key:"cardiologie", x:200, y:10,  w:65, h:38, label:"Cardiologie", color:"#6a1b9a" },
    { key:"radiologie",  x:5,   y:90,  w:65, h:38, label:"Radiologie",  color:"#d35400" },
    { key:"pediatrie",   x:102, y:90,  w:66, h:38, label:"Pédiatrie",   color:"#1e8449" },
    { key:"maternite",   x:200, y:90,  w:65, h:38, label:"Maternité",   color:"#a93226" },
    { key:"pharmacie",   x:102, y:158, w:66, h:30, label:"Pharmacie",   color:"#148f77" }
  ];

  var PATHS = {
    urgences:    [[135,215],[135,58],[37,58],[37,48]],
    accueil:     [[135,215],[135,48]],
    cardiologie: [[135,215],[135,58],[232,58],[232,48]],
    radiologie:  [[135,215],[135,138],[37,138],[37,128]],
    pediatrie:   [[135,215],[135,128]],
    maternite:   [[135,215],[135,138],[232,138],[232,128]],
    pharmacie:   [[135,215],[135,188]]
  };

  var DIRECTIONS = {
    urgences:    { duration:"2 min", distance:"180 m", steps:[
      "Depuis l'entrée, avancez tout droit sur l'allée centrale.",
      "Marchez environ 80 mètres jusqu'au grand carrefour.",
      "Tournez à gauche.",
      "Les Urgences se trouvent sur votre gauche, 30 mètres plus loin."
    ]},
    accueil:     { duration:"1 min", distance:"60 m", steps:[
      "Depuis l'entrée, avancez tout droit sur l'allée centrale.",
      "L'Accueil se trouve juste en face de vous."
    ]},
    cardiologie: { duration:"3 min", distance:"210 m", steps:[
      "Depuis l'entrée, avancez tout droit sur l'allée centrale.",
      "Marchez environ 80 mètres jusqu'au grand carrefour.",
      "Tournez à droite.",
      "La Cardiologie se trouve sur votre droite, 50 mètres plus loin."
    ]},
    radiologie:  { duration:"2 min", distance:"130 m", steps:[
      "Depuis l'entrée, avancez sur l'allée centrale.",
      "Marchez environ 50 mètres jusqu'au premier croisement.",
      "Tournez à gauche.",
      "La Radiologie se trouve sur votre gauche."
    ]},
    pediatrie:   { duration:"2 min", distance:"110 m", steps:[
      "Depuis l'entrée, avancez tout droit sur l'allée centrale.",
      "Après le premier croisement, la Pédiatrie est sur votre droite."
    ]},
    maternite:   { duration:"2 min", distance:"160 m", steps:[
      "Depuis l'entrée, avancez sur l'allée centrale.",
      "Marchez environ 50 mètres jusqu'au premier croisement.",
      "Tournez à droite.",
      "La Maternité se trouve sur votre droite, 50 mètres plus loin."
    ]},
    pharmacie:   { duration:"1 min", distance:"30 m", steps:[
      "Depuis l'entrée, avancez légèrement sur l'allée centrale.",
      "La Pharmacie est juste devant vous."
    ]}
  };

  // ── État ──────────────────────────────────────────────────────────────────────
  var _canvas, _ctx, _currentService;
  var _animFrame = null, _animProgress = 0, _stepIndex = 0, _pulse = 0;
  var _onStep = null, _showAll = false;
  var STEPS_H = 130; // hauteur réservée à la zone étapes

  // ── Dessin : coin arrondi sans arcTo ─────────────────────────────────────────
  function roundRect(x, y, w, h, r) {
    _ctx.beginPath();
    _ctx.moveTo(x + r, y);
    _ctx.lineTo(x + w - r, y);
    _ctx.quadraticCurveTo(x + w, y,     x + w, y + r);
    _ctx.lineTo(x + w, y + h - r);
    _ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    _ctx.lineTo(x + r, y + h);
    _ctx.quadraticCurveTo(x,     y + h, x,     y + h - r);
    _ctx.lineTo(x, y + r);
    _ctx.quadraticCurveTo(x,     y,     x + r, y);
    _ctx.closePath();
  }

  // ── Ligne en tirets sans setLineDash ─────────────────────────────────────────
  function dashedLine(x1, y1, x2, y2, dashLen, gapLen, color, lw) {
    var dx = x2 - x1, dy = y2 - y1;
    var total = Math.sqrt(dx * dx + dy * dy);
    if (total === 0) return;
    var ux = dx / total, uy = dy / total;
    var dist = 0, drawing = true;
    _ctx.strokeStyle = color;
    _ctx.lineWidth = lw || 3;
    _ctx.lineCap = "round";
    while (dist < total) {
      var seg = drawing ? dashLen : gapLen;
      var end = Math.min(dist + seg, total);
      if (drawing) {
        _ctx.beginPath();
        _ctx.moveTo(x1 + ux * dist, y1 + uy * dist);
        _ctx.lineTo(x1 + ux * end,  y1 + uy * end);
        _ctx.stroke();
      }
      dist = end;
      drawing = !drawing;
    }
  }

  // ── Chemin animé ─────────────────────────────────────────────────────────────
  function drawAnimPath(points, progress) {
    if (!points || points.length < 2) return;
    var segs = [], total = 0;
    for (var i = 1; i < points.length; i++) {
      var dx = points[i][0] - points[i-1][0];
      var dy = points[i][1] - points[i-1][1];
      var len = Math.sqrt(dx * dx + dy * dy);
      segs.push(len); total += len;
    }
    // Chemin gris (fond)
    for (var i = 1; i < points.length; i++) {
      dashedLine(points[i-1][0], points[i-1][1],
                 points[i][0],   points[i][1],
                 6, 5, "rgba(144,164,174,0.5)", 3);
    }
    // Portion animée (bleue)
    var target = total * Math.min(progress, 1), rem = target;
    for (var i = 0; i < segs.length; i++) {
      if (rem <= 0) break;
      var p1 = points[i], p2 = points[i + 1];
      var draw = Math.min(rem, segs[i]);
      var t = draw / segs[i];
      var ex = p1[0] + (p2[0] - p1[0]) * t;
      var ey = p1[1] + (p2[1] - p1[1]) * t;
      dashedLine(p1[0], p1[1], ex, ey, 6, 5, "#1a6fc4", 3);
      rem -= draw;
    }
  }

  // ── Rendu principal ───────────────────────────────────────────────────────────
  function draw() {
    if (!_ctx) return;
    _ctx.clearRect(0, 0, CW, CH);

    // Sol
    _ctx.fillStyle = "#f1f8e9";
    _ctx.fillRect(0, 0, CW, CH);

    // Allées
    _ctx.strokeStyle = "#cfd8dc";
    _ctx.lineWidth = 14;
    _ctx.lineCap = "round";
    _ctx.beginPath(); _ctx.moveTo(135, 215); _ctx.lineTo(135, 5);   _ctx.stroke();
    _ctx.beginPath(); _ctx.moveTo(5,   58);  _ctx.lineTo(265, 58);  _ctx.stroke();
    _ctx.beginPath(); _ctx.moveTo(5,   138); _ctx.lineTo(265, 138); _ctx.stroke();

    // Chemin animé
    if (_currentService && PATHS[_currentService]) {
      drawAnimPath(PATHS[_currentService], _animProgress);
    }

    // Bâtiments
    for (var i = 0; i < BUILDINGS.length; i++) {
      var b = BUILDINGS[i];
      var isTarget = (b.key === _currentService);

      _ctx.fillStyle = (_showAll || isTarget) ? b.color : "#90a4ae";
      roundRect(b.x, b.y, b.w, b.h, 5);
      _ctx.fill();

      if (isTarget) {
        _ctx.strokeStyle = "#ffffff";
        _ctx.lineWidth = 2;
        _ctx.stroke();
        // Marqueur épingle au-dessus du bâtiment
        var cx = b.x + b.w / 2;
        _ctx.fillStyle = b.color;
        _ctx.beginPath();
        _ctx.arc(cx, b.y - 8, 6, 0, Math.PI * 2);
        _ctx.fill();
        _ctx.fillStyle = "#ffffff";
        _ctx.beginPath();
        _ctx.arc(cx, b.y - 8, 2.5, 0, Math.PI * 2);
        _ctx.fill();
        _ctx.fillStyle = b.color;
        _ctx.beginPath();
        _ctx.moveTo(cx - 4, b.y - 5);
        _ctx.lineTo(cx, b.y);
        _ctx.lineTo(cx + 4, b.y - 5);
        _ctx.fill();
      }

      _ctx.fillStyle = "#ffffff";
      _ctx.font = isTarget ? "bold 8px sans-serif" : "8px sans-serif";
      _ctx.textAlign = "center";
      _ctx.fillText(b.label, b.x + b.w / 2, b.y + b.h / 2 + 3);
    }

    // Point VOUS (pulsation sans shadow)
    var pr = 6 + Math.sin(_pulse * 0.12) * 2;
    _ctx.fillStyle = "rgba(26,111,196,0.15)";
    _ctx.beginPath();
    _ctx.arc(135, 215, pr + 5, 0, Math.PI * 2);
    _ctx.fill();
    _ctx.fillStyle = "#1a6fc4";
    _ctx.beginPath();
    _ctx.arc(135, 215, 7, 0, Math.PI * 2);
    _ctx.fill();
    _ctx.fillStyle = "#ffffff";
    _ctx.font = "bold 6px sans-serif";
    _ctx.textAlign = "center";
    _ctx.fillText("VOUS", 135, 218);

    // Label entrée
    _ctx.fillStyle = "#37474f";
    _ctx.font = "bold 8px sans-serif";
    _ctx.fillText("Entree principale", 135, 215 + 18);

    _pulse++;
  }

  function animate() {
    _animProgress += 0.018;
    draw();
    if (_animProgress < 1) {
      _animFrame = _raf(animate);
    } else {
      _animProgress = 1;
      draw();
      _animFrame = null;
    }
  }

  // ── Guide pas à pas ───────────────────────────────────────────────────────────
  function renderStep() {
    var dirs = DIRECTIONS[_currentService];
    if (!dirs) return;
    var stepEl    = document.getElementById("map-step-text");
    var counterEl = document.getElementById("map-step-counter");
    var prevBtn   = document.getElementById("map-step-prev");
    var nextBtn   = document.getElementById("map-step-next");
    if (stepEl)    stepEl.textContent    = dirs.steps[_stepIndex];
    if (counterEl) counterEl.textContent = (_stepIndex + 1) + " / " + dirs.steps.length;
    if (prevBtn)   prevBtn.disabled      = (_stepIndex === 0);
    if (nextBtn)   nextBtn.disabled      = (_stepIndex === dirs.steps.length - 1);
    if (_onStep)   _onStep(dirs.steps[_stepIndex]);
  }

  // ── Normalisation du nom de service ──────────────────────────────────────────
  function normalize(name) {
    if (!name) return null;
    var n = name.toLowerCase()
      .replace(/[éèê]/g, "e")
      .replace(/â/g, "a")
      .replace(/î/g, "i");
    for (var i = 0; i < BUILDINGS.length; i++) {
      if (n.indexOf(BUILDINGS[i].key) !== -1) return BUILDINGS[i].key;
    }
    return null;
  }

  // ── Helpers internes ─────────────────────────────────────────────────────────

  function _openPanel() {
    var panel = document.getElementById("map-panel");
    if (!panel) return;
    panel.setAttribute("style", "display:block");
    var ic = document.getElementById("info-card");
    if (ic) ic.setAttribute("style", "display:none");
  }

  function _resizeCanvas(withSteps) {
    var headerH = 62;
    var stepsH  = withSteps ? STEPS_H : 0;
    var w = window.innerWidth;
    var h = window.innerHeight - headerH - stepsH;
    _canvas.setAttribute("style",
      "display:block;position:absolute;" +
      "top:" + headerH + "px;left:0;" +
      "width:" + w + "px;height:" + h + "px"
    );
  }

  function _showSteps() {
    var stepsDiv = document.getElementById("map-steps");
    var hintEl   = document.getElementById("map-hint");
    var gBtn     = document.getElementById("map-guide-btn");
    if (stepsDiv && stepsDiv.getAttribute("style") === "display:block") return;
    if (stepsDiv) stepsDiv.setAttribute("style", "display:block");
    if (hintEl)   hintEl.setAttribute("style",   "display:none");
    if (gBtn)     gBtn.setAttribute("style",      "display:none");
    _resizeCanvas(true);
    _stepIndex = 0;
    renderStep();
  }

  // ── API publique ──────────────────────────────────────────────────────────────
  return {

    init: function () {
      _canvas = document.getElementById("map-canvas");
      if (!_canvas || !_canvas.getContext) return;
      _canvas.width  = CW;
      _canvas.height = CH;
      try { _ctx = _canvas.getContext("2d"); } catch(e) { return; }

      var panel    = document.getElementById("map-panel");
      var stepsDiv = document.getElementById("map-steps");
      var infoCard = document.getElementById("info-card");
      if (panel)    panel.setAttribute("style",    "display:none");
      if (stepsDiv) stepsDiv.setAttribute("style", "display:none");
      if (infoCard) infoCard.setAttribute("style", "display:none");

      var closeBtn = document.getElementById("map-close");
      var prevBtn  = document.getElementById("map-step-prev");
      var nextBtn  = document.getElementById("map-step-next");

      if (closeBtn) closeBtn.onclick = function () { HospitalMap.hide(); };

      if (prevBtn) prevBtn.onclick = function () {
        if (_stepIndex > 0) { _stepIndex--; renderStep(); }
      };
      if (nextBtn) nextBtn.onclick = function () {
        var dirs = DIRECTIONS[_currentService];
        if (dirs && _stepIndex < dirs.steps.length - 1) { _stepIndex++; renderStep(); }
      };

      // Clic sur le canvas : bâtiment (mode all) ou démarrage guide
      _canvas.style.cursor = "pointer";
      _canvas.onclick = function (e) {
        if (_showAll) {
          var rect   = _canvas.getBoundingClientRect();
          var scaleX = CW / (rect.width  || CW);
          var scaleY = CH / (rect.height || CH);
          var cx = (e.clientX - rect.left) * scaleX;
          var cy = (e.clientY - rect.top)  * scaleY;
          for (var i = 0; i < BUILDINGS.length; i++) {
            var b = BUILDINGS[i];
            if (cx >= b.x && cx <= b.x + b.w && cy >= b.y && cy <= b.y + b.h) {
              HospitalMap.showWithGuide(b.key);
              return;
            }
          }
        } else if (_currentService) {
          _showSteps();
        }
      };
    },

    // Affiche le plan de tous les services (pas de destination précise)
    showAll: function () {
      _showAll        = true;
      _currentService = null;
      _animProgress   = 0;
      _pulse          = 0;

      var titleEl  = document.getElementById("map-service-title");
      var distEl   = document.getElementById("map-distance");
      var durEl    = document.getElementById("map-duration");
      var hintEl   = document.getElementById("map-hint");
      var stepsDiv = document.getElementById("map-steps");
      var infoEl   = document.getElementById("map-info");
      if (titleEl)  titleEl.textContent = "Plan de l'hôpital";
      if (distEl)   distEl.textContent  = "";
      if (durEl)    durEl.textContent   = "";
      if (infoEl)   infoEl.setAttribute("style", "display:none");
      if (stepsDiv) stepsDiv.setAttribute("style", "display:none");
      if (hintEl)   hintEl.setAttribute("style",   "display:block");

      _openPanel();
      _resizeCanvas(false);
      if (_animFrame) { _caf(_animFrame); _animFrame = null; }
      animate();
    },

    // Affiche le plan avec itinéraire vers un service
    show: function (serviceName) {
      var key = normalize(serviceName);
      if (!key) return;

      _showAll        = false;
      _currentService = key;
      _animProgress   = 0;
      _stepIndex      = 0;
      _pulse          = 0;

      var panel = document.getElementById("map-panel");
      if (!panel) return;

      var titleEl = document.getElementById("map-service-title");
      for (var i = 0; i < BUILDINGS.length; i++) {
        if (BUILDINGS[i].key === key && titleEl) {
          titleEl.textContent = BUILDINGS[i].label;
          break;
        }
      }

      var d      = DIRECTIONS[key] || {};
      var distEl = document.getElementById("map-distance");
      var durEl  = document.getElementById("map-duration");
      var infoEl = document.getElementById("map-info");
      if (distEl) distEl.textContent = d.distance || "";
      if (durEl)  durEl.textContent  = d.duration  || "";
      if (infoEl) infoEl.setAttribute("style", "");

      var stepsDiv = document.getElementById("map-steps");
      var hintEl   = document.getElementById("map-hint");
      var gBtn     = document.getElementById("map-guide-btn");
      if (stepsDiv) stepsDiv.setAttribute("style", "display:none");
      if (hintEl)   hintEl.setAttribute("style",   "display:none");
      if (gBtn)     gBtn.setAttribute("style",      "display:none");

      _openPanel();
      _resizeCanvas(false);
      if (_animFrame) { _caf(_animFrame); _animFrame = null; }
      animate();
    },

    hide: function () {
      var panel = document.getElementById("map-panel");
      if (panel) panel.setAttribute("style", "display:none");
      if (_animFrame) { _caf(_animFrame); _animFrame = null; }
      _currentService = null;
      _showAll        = false;
    },

    setStepCallback: function (fn) { _onStep = fn; },

    showWithGuide: function (serviceName) {
      HospitalMap.show(serviceName);
      setTimeout(_showSteps, 150);
    },

    normalize: normalize
  };
})();

// Initialisation directe (pas de DOMContentLoaded — scripts en bas de body)
HospitalMap.init();
