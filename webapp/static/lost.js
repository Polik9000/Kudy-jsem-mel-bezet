/* "Ztratil jsem se u kontroly", a look back after the race (no help during it: the rules forbid a phone and any
   other aid there). The places near the control where the track shows trouble, each with what was there and the
   way back; or, for a race without a track or a place the track missed, tap where you roughly were (or only the
   control and around it) and how unsure you were: the server answers with the advice (views/lost.py).
   Big buttons, no hover, one tap = one thing. */
(function () {
  "use strict";
  var Z = window.OBZ, map = null, layers = {}, overlays = {};
  var k = null, pos = null, r = Z.r0 || 50, around = false, mode = Z.back ? "po" : "misto", asked = 0;
  var $ = function (id) { return document.getElementById(id); };

  function esc(t) {
    return String(t === null || t === undefined ? "" : t).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function api(url, method, body) {
    return fetch(url, {
      method: method, headers: { "Content-Type": "application/json", "X-CSRF-Token": Z.csrf },
      body: body ? JSON.stringify(body) : undefined
    }).then(function (res) {
      if (!res.ok) { throw new Error(String(res.status)); }
      return res.json();
    });
  }
  function control(n) {
    for (var i = 0; i < Z.controls.length; i++) { if (Z.controls[i].k === n) { return Z.controls[i]; } }
    return null;
  }
  function say(text) {
    var el = $("z-mapa-stav");
    el.hidden = !text;
    el.textContent = text || "";
  }

  // ---- the map: the same placed pictures as the race page
  function init() {
    map = L.map("z-mapa", { zoomSnap: 0.25, minZoom: 11, maxZoom: 21, doubleClickZoom: false, attributionControl: true });
    map.attributionControl.setPrefix(false);
    map.attributionControl.addAttribution("mapa © pořadatel závodu");
    map.createPane("mapimg").style.zIndex = 200;
    ["maponly", "course"].forEach(function (kind) {
      var m = Z.maps[kind];
      if (!m) { return; }
      overlays[kind] = L.imageOverlay.rotated(m.url, L.latLng(m.corners[0]), L.latLng(m.corners[1]),
        L.latLng(m.corners[2]), { opacity: 0.95, pane: "mapimg" });
      overlays[kind].on("load", function () {
        if (m.header_px) { this._rawImage.style.clipPath = "inset(" + m.header_px + "px 0 0 0)"; }
      });
    });
    $("z-trat").parentNode.hidden = !(overlays.course && overlays.maponly);
    $("z-trat").checked = !!overlays.course;
    showMap();
    ["controls", "track", "advice", "you"].forEach(function (g) { layers[g] = L.layerGroup().addTo(map); });
    var all = Z.controls.map(function (c) { return c.at; });
    if (all.length) { map.fitBounds(L.latLngBounds(all).pad(0.1)); }
    map.on("click", function (ev) {
      if (mode !== "misto" || k === null) { return; }
      pos = [ev.latlng.lat, ev.latlng.lng];
      around = false;
      ask();
    });
  }
  function showMap() {
    var course = $("z-trat").checked && overlays.course;
    ["maponly", "course"].forEach(function (kind) {
      if (!overlays[kind]) { return; }
      var on = kind === "course" ? course : !course;
      if (on && !map.hasLayer(overlays[kind])) { overlays[kind].addTo(map); }
      if (!on && map.hasLayer(overlays[kind])) { map.removeLayer(overlays[kind]); }
    });
  }

  // ---- choosing the control
  function pick(n) {
    k = n;
    pos = null;
    around = false;
    Array.prototype.forEach.call(document.querySelectorAll(".ob-ztr-cip"), function (b) {
      b.setAttribute("aria-pressed", String(Number(b.dataset.k) === n));
    });
    var c = control(n);
    if (!c) { return; }
    // only the control picked is marked: the map with the course has its circles (in the size of its scale)
    layers.controls.clearLayers();
    L.circle(c.at, { radius: 20, className: "ob-ztr-kolecko", interactive: false }).addTo(layers.controls);
    history.replaceState(null, "", "#k" + n);
    map.setView(c.at, Math.max(map.getZoom(), 17));
    $("z-popis").value = c.desc || "";
    $("z-popis-stav").textContent = "";
    clearAdvice();
    $("z-pokyn").textContent = "Kontrola " + n + ": ťukni do mapy, kde jsi asi byl, když ses ztratil.";
    if (mode === "po") { loadBack(); }
  }
  function clearAdvice() {
    layers.advice.clearLayers();
    layers.you.clearLayers();
    layers.track.clearLayers();
    $("z-rada").hidden = true;
  }

  // ---- the advice
  function ask() {
    if (k === null) { say("Nejdřív vyber kontrolu nahoře."); return; }
    var body = { k: k, r: r };
    if (pos && !around) { body.lat = pos[0]; body.lon = pos[1]; }
    var mine = ++asked;
    say("Počítám…");
    api(Z.advice, "POST", body).then(function (a) {
      if (mine !== asked) { return; }
      say("");
      show(a, a.sentences, a.note, a.names);
    }, function (err) {
      if (mine !== asked) { return; }
      say(err.message === "409" ? "Mapa závodu se mezitím změnila; obnov stránku." : "Radu se nepodařilo spočítat, zkus to znovu.");
    });
  }
  function show(a, sentences, note, names) {
    layers.advice.clearLayers();
    layers.you.clearLayers();
    L.circle(a.pos, { radius: a.r, className: "ob-ztr-kruh", interactive: false }).addTo(layers.you);
    if (!a.no_runner) {
      L.circleMarker(a.pos, { radius: 7, className: "ob-ztr-ty", interactive: false }).addTo(layers.you);
    }
    if (a.route && a.route.length > 1) {
      L.polyline(a.route, { className: "ob-ztr-cesta", interactive: false }).addTo(layers.advice);
    }
    a.helpers.forEach(function (h, i) {
      var big = i === a.pick;
      L.circleMarker(h.at, { radius: big ? 13 : 9, className: "ob-ztr-bod" + (h.sure ? " jisty" : "") + (big ? " vybrany" : ""),
        interactive: false }).addTo(layers.advice);
      L.marker(h.at, { icon: L.divIcon({ className: "ob-ztr-cislo", html: String(i + 1), iconSize: [18, 18] }),
        interactive: false }).addTo(layers.advice);
    });
    var c = control(k);
    var pts = [a.pos, c.at].concat(a.helpers.length && a.pick !== null ? [a.helpers[a.pick].at] : []);
    map.fitBounds(L.latLngBounds(pts).pad(0.35), { maxZoom: 18 });
    $("z-note").hidden = !note;
    $("z-note").textContent = note || "";
    $("z-vety").innerHTML = (sentences || []).map(function (t) { return "<p>" + esc(t) + "</p>"; }).join("");
    $("z-seznam").innerHTML = (names || []).map(function (n) {
      return "<li" + (n.sure ? " class='jisty'" : "") + ">" + esc(n.text) + "</li>";
    }).join("");
    $("z-body").hidden = !(names && names.length);
    $("z-rada").hidden = false;
  }

  // ---- after the race
  function loadBack() {
    clearAdvice();
    $("z-mista").innerHTML = "<p class='hint'>Načítám…</p>";
    fetch(Z.back + "?k=" + k).then(function (res) {
      if (!res.ok) { throw new Error(String(res.status)); }
      return res.json();
    }).then(function (d) {
      if (d.track && d.track.length > 1) {
        L.polyline(d.track, { className: "ob-ztr-stopa", interactive: false }).addTo(layers.track);
      }
      if (!d.moments.length) {
        $("z-mista").innerHTML = "<p>U téhle kontroly stopa nic takového neukazuje.</p>";
        return;
      }
      $("z-mista").innerHTML = "";
      d.moments.forEach(function (m, i) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "btn ob-ztr-misto";
        b.textContent = (i + 1) + ". " + m.head;
        b.setAttribute("aria-pressed", "false");
        b.addEventListener("click", function () { moment(m, b); });
        $("z-mista").appendChild(b);
        L.circleMarker(m.at, { radius: 8, className: "ob-ztr-misto-bod", interactive: false }).addTo(layers.track);
      });
      moment(d.moments[0], $("z-mista").firstChild);
    }, function () {
      $("z-mista").innerHTML = "<p>Místa se nepodařilo načíst.</p>";
    });
  }
  function moment(m, button) {
    Array.prototype.forEach.call(document.querySelectorAll(".ob-ztr-misto"), function (b) {
      b.setAttribute("aria-pressed", String(b === button));
    });
    show(m.advice, [m.head, m.seen].concat(m.back.length ? ["Kudy zpět: " + m.back[0]].concat(m.back.slice(1)) : []),
      null, []);
  }
  function setMode(m) {
    mode = m;
    $("z-misto").setAttribute("aria-pressed", String(m === "misto"));
    $("z-po").setAttribute("aria-pressed", String(m === "po"));
    $("z-misto-panel").hidden = m !== "misto";
    $("z-po-panel").hidden = m !== "po";
    clearAdvice();
    if (m === "po" && k !== null) { loadBack(); }
  }

  // ---- buttons
  Array.prototype.forEach.call(document.querySelectorAll(".ob-ztr-cip"), function (b) {
    b.addEventListener("click", function () { pick(Number(b.dataset.k)); });
  });
  Array.prototype.forEach.call(document.querySelectorAll(".ob-ztr-r button"), function (b) {
    b.addEventListener("click", function () {
      r = Number(b.dataset.r);
      Array.prototype.forEach.call(document.querySelectorAll(".ob-ztr-r button"), function (o) {
        o.setAttribute("aria-pressed", String(o === b));
      });
      if (pos || around) { ask(); }
    });
  });
  $("z-okoli").addEventListener("click", function () { around = true; ask(); });
  $("z-trat").addEventListener("change", showMap);
  if ($("z-misto")) {
    $("z-misto").addEventListener("click", function () { setMode("misto"); });
    $("z-po").addEventListener("click", function () { setMode("po"); });
  }
  $("z-popis-ulozit").addEventListener("click", function () {
    if (k === null) { return; }
    $("z-popis-stav").textContent = "Ukládám…";
    api(Z.desc, "POST", { k: k, text: $("z-popis").value }).then(function (d) {
      var c = control(d.k);
      if (c) { c.desc = d.desc; }
      $("z-popis-stav").textContent = d.desc ? "Uloženo." : "Popis smazaný.";
      if (pos || around) { ask(); }
    }, function () { $("z-popis-stav").textContent = "Nepodařilo se uložit."; });
  });

  init();
  var want = /^#k(\d+)$/.exec(location.hash);
  if (want && control(Number(want[1]))) { pick(Number(want[1])); }
  else if (Z.controls.length) { pick(Z.controls[0].k); }
})();
