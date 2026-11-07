/* Race page: the map from the KMZ under the GPS track, best routes with alternatives, forbidden crossings,
   leg table and notes. Everything comes from data.json; saving a note returns the legs again, recalculated.
   Colours are CSS classes (static/ob.css) built on the club stylesheet's variables. */
(function () {
  "use strict";
  var T = window.obT;               // English for the Czech texts of this script (see ob.js)
  var OB_LANG = (window.OBAPP && window.OBAPP.lang) || "cs";
  var OB = window.OB, D = null, map = null, selected = null, drawing = null, mode = null, saving = 0;
  var groups = {}, overlays = {};
  var lines = {}, altLines = [];        // layers of each leg (track, best route) and of the selected leg's alternatives
  var LEG_GROUPS = ["best", "track", "planned", "stops", "marks"];  // the groups that hold what belongs to one leg
  var whole = null;                     // the bounds of the whole course and track
  var noteTimer = null, sent = 0, shown = 0;  // a note waiting to be saved; order of the saves and of their answers
  var planTimer = null;                 // set while the page waits for the worker to price a planned route
  var $ = function (id) { return document.getElementById(id); };
  // the bar over the map: what the next clicks into the map draw
  var DRAWING = {
    plan: T("Plánovaný postup: klikáním do mapy přidávej body od kontroly ke kontrole. Dvojklik nebo Hotovo uloží."),
    forbidden: T("Zakázaná čára: klikáním do mapy přidávej její body. Dvojklik nebo Hotovo uloží."),
    hard: T("Těžko překonatelná čára: klikáním do mapy přidávej její body. Dvojklik nebo Hotovo uloží."),
    refresh: T("Občerstvovačka: klikni do mapy na místo, kde stála."),
    corrected: T("Oprava stopy: klikáním do mapy přidávej body, kudy jsi na úseku opravdu běžel (začátek a konec jsou kontroly). Dvojklik nebo Hotovo uloží.")
  };

  function mmss(s, sign) {
    if (s === null || s === undefined) { return ""; }
    var neg = s < 0, v = Math.round(Math.abs(s));
    return (neg ? "-" : (sign && v ? "+" : "")) + Math.floor(v / 60) + ":" + ("0" + (v % 60)).slice(-2);
  }
  function esc(t) {
    return String(t === null || t === undefined ? "" : t).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function grade(loss) { return loss < 20 ? 0 : loss < 60 ? 1 : loss < 180 ? 2 : 3; }
  function api(url, method, body, leaving) {
    return fetch(url, {
      method: method, headers: { "Content-Type": "application/json", "X-CSRF-Token": OB.csrf },
      body: body ? JSON.stringify(body) : undefined, keepalive: !!leaving  // keepalive: sent even as the page closes
    }).then(function (r) {
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.json();
    });
  }
  function legPoints(leg) {
    var pts = [], i;
    for (i = leg.a; i <= leg.b; i++) { pts.push([D.track.lat[i], D.track.lon[i]]); }
    return pts;
  }
  // a point `m` metres from [lat, lon] in direction `deg` (0 = north), good enough at map scale
  function offset(p, m, deg) {
    var r = deg * Math.PI / 180;
    return [p[0] + m * Math.cos(r) / 111195, p[1] + m * Math.sin(r) / (111195 * Math.cos(p[0] * Math.PI / 180))];
  }

  // the note in the corner of the map: what is still loading, or what went wrong (with a button to try again)
  function state(text, retry) {
    var el = $("map-stav");
    el.hidden = !text;
    el.textContent = text || "";
    if (retry) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "btn btn-maly";
      b.textContent = "Zkusit znovu";
      b.addEventListener("click", retry);
      el.appendChild(document.createTextNode(" "));
      el.appendChild(b);
    }
  }
  function load() {
    state(T("Načítám stopu a postupy…"));
    fetch(OB.data).then(function (r) {
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.json();
    }).then(function (d) { state(""); init(d); }, function () { state(T("Data závodu se nepodařilo načíst."), load); });
  }
  load();

  // The page loads itself again when a new analysis is ready (ob.js), but not under the runner's hands:
  // not while a line is being drawn or a note is being written or saved.
  function guard() {
    if (drawing || mode || saving || noteTimer || document.activeElement === $("n-text")) {
      document.body.dataset.noReload = "1";
    } else {
      delete document.body.dataset.noReload;
    }
  }

  function init(d) {
    D = d;
    if (D.rerouting) { document.body.setAttribute("data-obnovit", ""); }
    map = L.map("map", { zoomSnap: 0.25, minZoom: 11, maxZoom: 21, doubleClickZoom: false, attributionControl: true });
    map.attributionControl.setPrefix(false);
    map.attributionControl.addAttribution(T("mapa © pořadatel závodu") + (D.osm ? " · " + T("překážky © přispěvatelé OpenStreetMap") : ""));
    map.createPane("mapimg").style.zIndex = 200;
    var all = D.track.lat.map(function (la, i) { return [la, D.track.lon[i]]; })
      .concat(D.course.map(function (c) { return [c.lat, c.lon]; }));
    whole = L.latLngBounds(all).pad(0.08);
    map.fitBounds(whole);
    ["maponly", "course"].forEach(function (k) {
      if (!D.maps[k]) { return; }
      var c = D.maps[k].corners, top = D.maps[k].header_px;
      overlays[k] = L.imageOverlay.rotated(D.maps[k].url, L.latLng(c[0]), L.latLng(c[1]), L.latLng(c[2]),
        { opacity: 0.92, pane: "mapimg" });
      overlays[k].on("load", function () {
        this.loaded = true;
        state("");
        // hide the Livelox header bar at the top of the exported picture
        if (top) { this._rawImage.style.clipPath = "inset(" + top + "px 0 0 0)"; }
      });
    });
    $("l-course").hidden = !(overlays.maponly && overlays.course);
    $("c-course").checked = !overlays.maponly;
    showMap();
    ["barriers", "controls", "best", "track", "orez", "planned", "stops", "marks", "refresh", "catch", "sel", "draw"].forEach(function (k) {
      groups[k] = L.layerGroup().addTo(map);
    });
    draw();
    trimPreview();
    table();
    strip();
    totals();
    watchPlans();

    $("c-map").addEventListener("change", showMap);
    $("c-course").addEventListener("change", showMap);
    $("c-alts").addEventListener("change", mark);
    $("c-prumer").addEventListener("change", mark);
    $("c-zachyt").addEventListener("change", mark);
    // opening "if you got lost" shows its points on the map
    $("p-ztrata").addEventListener("toggle", function () {
      if (this.open && !$("c-zachyt").checked) { $("c-zachyt").checked = true; mark(); }
    });
    ["n-stop", "n-lost", "n-green", "n-fatigue", "n-text"].forEach(function (id) {
      $(id).addEventListener("change", function () { saveNote(); });
    });
    // the text of a note is saved a moment after the last key, not only when the field is left
    $("n-text").addEventListener("input", function () {
      clearTimeout(noteTimer);
      noteTimer = setTimeout(saveNote, 900);
      $("p-saved").textContent = T("Neuloženo…");
      guard();
    });
    window.addEventListener("pagehide", function () { if (noteTimer) { saveNote(null, true); } });
    $("n-text").addEventListener("focus", guard);
    $("n-text").addEventListener("blur", guard);
    $("b-zpet").addEventListener("click", function () { select(null); });
    overview();
    $("b-prev").addEventListener("click", function () { step(-1); });
    $("b-next").addEventListener("click", function () { step(1); });
    $("b-draw").addEventListener("click", function () { startDrawing("plan"); });
    $("b-undo").addEventListener("click", function () { if (drawing) { drawing.pop(); drawLine(); } });
    $("b-done").addEventListener("click", finishDrawing);
    $("b-cancel").addEventListener("click", cancel);
    $("b-clear").addEventListener("click", function () { cancel(); saveNote({ planned: null }); });
    $("b-oprava").addEventListener("click", function () { startDrawing("corrected"); });
    $("b-gps").addEventListener("click", function () { cancel(); saveCorrection(null); });
    Array.prototype.forEach.call(document.querySelectorAll("[data-ob-add]"), function (b) {
      b.addEventListener("click", function () { toggleMode(b.dataset.obAdd); });
    });
    // Esc gives up what is being drawn, Enter saves it (unless the key belongs to a field or a button)
    document.addEventListener("keydown", function (ev) {
      var field = /^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName);
      if (!drawing && !mode) {
        // Esc goes back from a leg to the whole course
        if (ev.key === "Escape" && selected && !field) { select(null); }
        // layer keys shown in the panel over the map: M map, T map with the course, 1-3 the other layers
        var layer = { m: "c-map", t: "c-course", 1: "c-alts", 2: "c-prumer", 3: "c-zachyt" }[ev.key.toLowerCase()];
        if (layer && !field && !ev.altKey && !ev.ctrlKey && !ev.metaKey && $(layer) && !$(layer).closest("[hidden]") &&
            $("mapa").classList.contains("aktivni")) {
          $(layer).checked = !$(layer).checked;
          $(layer).dispatchEvent(new Event("change"));
        }
        // ← and → go to the previous and the next leg while the map tab is open
        if ((ev.key === "ArrowLeft" || ev.key === "ArrowRight") && !field && !ev.altKey && !ev.ctrlKey && !ev.metaKey &&
            $("mapa").classList.contains("aktivni")) {
          ev.preventDefault();
          step(ev.key === "ArrowLeft" ? -1 : 1);
        }
        return;
      }
      if (ev.key === "Escape") {
        cancel();
      } else if (ev.key === "Enter" && drawing && !/^(INPUT|TEXTAREA|SELECT|BUTTON|A)$/.test(ev.target.tagName)) {
        ev.preventDefault();
        finishDrawing();
      }
    });
    map.on("click", function (ev) {
      if (mode === "refresh") {
        toggleMode(null);
        api(OB.refreshments, "POST", { lat: ev.latlng.lat, lon: ev.latlng.lng }).then(update);
      } else if (drawing) {
        drawing.push([ev.latlng.lat, ev.latlng.lng]);
        drawLine();
      }
    });
    map.on("dblclick", function () { if (drawing) { drawing.pop(); finishDrawing(); } });
    // the map sits in a tab: Leaflet has to measure itself again when the tab is shown
    document.addEventListener("ob-tab", function (ev) {
      if (ev.detail === "mapa") { map.invalidateSize(); }
    });
    // links to a leg from the other tabs (split-time table)
    Array.prototype.forEach.call(document.querySelectorAll("a[data-usek]"), function (a) {
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        document.dispatchEvent(new CustomEvent("ob-tab-show", { detail: "mapa" }));
        select(Number(a.dataset.usek), true);
      });
    });
    if (location.hash.indexOf("#usek-") === 0) { select(Number(location.hash.slice(6))); }
  }

  // --- modes of the map click: refreshment point, forbidden line ---
  // The buttons that start them are on the settings tab; the map and the bar that says what to do are here.
  function toggleMode(m) {
    if (drawing) { stopDrawing(); }
    mode = mode === m ? null : m;
    if (mode) { document.dispatchEvent(new CustomEvent("ob-tab-show", { detail: "mapa" })); }
    if (mode === "forbidden" || mode === "hard") { startDrawing(mode); }
    bar();
    if (mode) { $("kresleni").scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  }
  // the bar over the map, the pressed button and the cursor, by what is being drawn
  function bar() {
    var kind = drawing ? drawing.kind : mode;
    $("kresleni").hidden = !kind;
    $("k-text").textContent = kind ? DRAWING[kind] : "";
    $("b-undo").hidden = $("b-done").hidden = !drawing;
    $("b-draw").hidden = !!drawing && drawing.kind === "plan";
    $("b-oprava").hidden = !!drawing && drawing.kind === "corrected";
    $("map").style.cursor = kind ? "crosshair" : "";
    Array.prototype.forEach.call(document.querySelectorAll("[data-ob-add]"), function (b) {
      b.setAttribute("aria-pressed", mode && b.dataset.obAdd === mode ? "true" : "false");
    });
    guard();
  }
  function cancel() {
    mode = null;
    stopDrawing();
  }

  function showMap() {
    var course = $("c-course").checked || !overlays.maponly, on = $("c-map").checked;
    Object.keys(overlays).forEach(function (k) { map.removeLayer(overlays[k]); });
    var o = course && overlays.course ? overlays.course : overlays.maponly || overlays.course;
    if (on && o) {
      o.addTo(map);
      if (!o.loaded) {
        state(T("Načítám obrázek mapy…"));
        o._rawImage.addEventListener("error", function () { state(T("Obrázek mapy se nepodařilo načíst.")); });
      }
    }
  }

  function draw() {
    Object.keys(groups).forEach(function (k) { if (k !== "draw" && k !== "orez") { groups[k].clearLayers(); } });
    var n = D.course.length;
    // out-of-bounds areas read from the purple hatching of the map with the course
    (D.areas || []).forEach(function (ring) {
      L.polygon(ring, { className: "ob-zakaz-plocha", weight: 2, opacity: 0.9, fillOpacity: 0.22, interactive: false })
        .addTo(groups.barriers);
    });
    // forbidden crossings: from OpenStreetMap (thin) and drawn by hand (thick), plus the places where crossing is allowed
    ((D.osm && D.osm.lines) || []).forEach(function (b) {
      L.polyline(b.line, { className: "ob-zakaz-osm", weight: 3, opacity: 0.75, dashArray: b.kind === "hard" ? "6 5" : null, interactive: false })
        .addTo(groups.barriers);
    });
    ((D.osm && D.osm.crossings) || []).forEach(function (p) {
      L.circleMarker(p, { className: "ob-prechod", radius: 5, weight: 2, fillOpacity: 0.9 })
        .bindTooltip(T("přechod, most nebo podchod (OpenStreetMap): tudy se smí")).addTo(groups.barriers);
    });
    (D.barriers || []).forEach(function (b) {
      var line = L.polyline(b.line, { className: "ob-zakaz", weight: 5, opacity: 0.9, dashArray: b.kind === "hard" ? "8 6" : null })
        .addTo(groups.barriers);
      var box = document.createElement("div"), btn = document.createElement("button");
      box.textContent = (b.kind === "hard" ? T("Těžko překonatelné (velmi pomalé).") : T("Zakázaný přechod (sdílený pro závod).")) + " " +
        (b.by ? T("Přidal: %(by)s.", { by: b.by }) + " " : "");
      btn.textContent = T("Smazat");
      btn.className = "btn btn-maly";
      btn.addEventListener("click", function () { api(OB.barriers + "/" + b.id, "DELETE").then(update); });
      if (b.mine) { box.appendChild(btn); }  // shared things are taken away only by whoever added them
      line.bindPopup(box);
    });
    D.course.forEach(function (c, i) {
      var p = [c.lat, c.lon], o = { className: "ob-trat", weight: 2, fill: false, interactive: false };
      if (i === 0) {
        L.polygon([offset(p, 30, 0), offset(p, 30, 120), offset(p, 30, 240)], o).addTo(groups.controls);
      } else {
        L.circle(p, Object.assign({ radius: 22 }, o)).addTo(groups.controls);
        if (i === n - 1) {
          L.circle(p, Object.assign({ radius: 15 }, o)).addTo(groups.controls);
        } else {
          L.marker(offset(p, 34, 45), {
            interactive: false,
            icon: L.divIcon({ className: "ctrl-label", html: String(i), iconSize: [24, 16], iconAnchor: [4, 12] })
          }).addTo(groups.controls);
        }
      }
    });
    lines = {};
    D.legs.forEach(function (leg) {
      // all: every layer of the leg with the group it is drawn in, so mark() can take the other legs off the map
      var l = lines[leg.n] = { all: [] };
      var put = function (layer, group) { l.all.push([layer, group]); return layer; };
      if (leg.best_route) {
        l.under = put(L.polyline(leg.best_route, { className: "ob-podklad", weight: 6, opacity: 0.8, interactive: false }), "best");
        l.best = put(L.polyline(leg.best_route, { className: "ob-best", weight: 3, opacity: 0.95, dashArray: "8 6", interactive: false }), "best");
      }
      if (leg.note.corrected) {
        // where the runner really ran (drawn by hand): it stands for the track, the GPS line stays faint under it
        put(L.polyline(leg.note.corrected, { className: "ob-oprava", weight: 4, dashArray: "6 4", interactive: false })
          .bindTooltip(leg.name + ": " + T("opraveno ručně"), { permanent: false }), "track");
      }
      l.track = put(L.polyline(legPoints(leg), { className: "ob-z" + grade(leg.loss) + (leg.note.corrected ? " ob-gps-slaba" : ""),
                                                 weight: 4, opacity: leg.note.corrected ? 0.35 : 0.95 }), "track")
        .bindTooltip(leg.name + ": " + mmss(leg.time) + (leg.loss >= 20 ? ", " + T("ztráta %(t)s", { t: mmss(leg.loss) }) : "") +
                     (leg.mistake ? " · " + leg.mistake.label : ""), { sticky: true })
        .on("click", function (ev) {
          if (drawing || mode) { return; }  // the click belongs to what is being drawn: let the map have it
          L.DomEvent.stopPropagation(ev);
          select(leg.n);
        });
      if (leg.note.planned) {
        put(L.polyline(leg.note.planned, { className: "ob-plan", weight: 3, dashArray: "2 6", interactive: false }), "planned");
      }
      leg.stops.forEach(function (s) {
        put(L.circleMarker([s.lat, s.lon], { className: "ob-stani", radius: Math.min(12, 4 + s.dur / 20), weight: 1, fillOpacity: 0.85 })
          .bindTooltip(T("stání %(s)s s", { s: Math.round(s.dur) })), "stops");
      });
      if (leg.mistake && leg.mistake.at) {
        put(L.circleMarker(leg.mistake.at, { className: "ob-chyba-misto", radius: 7, weight: 2, fillOpacity: 0.25 })
          .bindTooltip(leg.name + ": " + leg.mistake.label), "marks");
      }
    });
    D.refreshments.forEach(function (r) {
      var m = L.marker([r.lat, r.lon], {
        icon: L.divIcon({ className: "refresh-icon", html: "O", iconSize: [22, 22], iconAnchor: [11, 11] })
      }).addTo(groups.refresh);
      var box = document.createElement("div"), btn = document.createElement("button");
      box.textContent = T("Občerstvovačka: zastávky do 30 m od ní jsou schválné.") + " " + (r.by ? T("Přidal: %(by)s.", { by: r.by }) + " " : "");
      btn.textContent = T("Smazat");
      btn.className = "btn btn-maly";
      btn.addEventListener("click", function () { api(OB.refreshments + "/" + r.id, "DELETE").then(update); });
      if (r.mine) { box.appendChild(btn); }
      m.bindPopup(box);
    });
    mark();
  }

  // Which leg is selected, shown without drawing the map again: only the lines of that leg (thicker), its
  // alternatives (numbered as in the panel), attack point and backstop, the row of the table and the chip of
  // the strip. With no leg selected the whole course is there.
  function mark() {
    // The lines of the other legs are taken off the map, not made transparent: an invisible track would still
    // catch the clicks. The groups are filled again kind by kind, so tracks stay above best routes.
    LEG_GROUPS.forEach(function (g) {
      groups[g].clearLayers();
      D.legs.forEach(function (leg) {
        if (selected && leg.n !== selected) { return; }
        ((lines[leg.n] || {}).all || []).forEach(function (x) { if (x[1] === g) { groups[g].addLayer(x[0]); } });
      });
    });
    D.legs.forEach(function (leg) {
      var l = lines[leg.n], sel = selected === leg.n;
      if (!l) { return; }
      l.track.setStyle({ weight: sel ? 7 : 4 });
      if (l.best) {
        l.under.setStyle({ weight: sel ? 8 : 6 });
        l.best.setStyle({ weight: sel ? 5 : 3 });
      }
    });
    groups.sel.clearLayers();
    altLines = [];
    var leg = current();
    if (leg && $("c-alts").checked) {
      (leg.alts || []).forEach(function (a, k) {
        altLines[k] = L.polyline(a.route, { className: "ob-alt", weight: 3, opacity: 0.6, dashArray: "3 7" })
          .bindTooltip(T("možnost %(n)s", { n: k + 2 }) + ": " + mmss(a.time) + " (" + mmss(a.delta, true) + ")", { sticky: true })
          .on("mouseover", function () { lit(k, true); }).on("mouseout", function () { lit(k, false); })
          .addTo(groups.sel);
        altLines[k].bringToBack();
        // the number of the alternative, a third of the way along it (the middle is where routes meet most often)
        L.marker(a.route[Math.floor(a.route.length / 3)], {
          interactive: false,
          icon: L.divIcon({ className: "ob-alt-cislo", html: String(k + 2), iconSize: [18, 18], iconAnchor: [9, 9] })
        }).addTo(groups.sel);
      });
    }
    // the best route of an average runner (oroute/generic.py), only where it differs from the runner's own
    var avg = leg && leg.generic;
    if (avg && avg.route && $("c-prumer").checked) {
      L.polyline(avg.route, { className: "ob-prumer", weight: 3, opacity: 0.9, dashArray: "1 6", lineCap: "round" })
        .bindTooltip(T("postup průměrného běžce: tobě by trval %(t)s", { t: mmss(avg.time) }), { sticky: true })
        .addTo(groups.sel).bringToBack();
    }
    if (leg && leg.attack) {
      L.circleMarker([leg.attack.lat, leg.attack.lon], { className: "ob-nabeh", radius: 7, weight: 3, fillOpacity: 0.9 })
        .bindTooltip(T("náběhový bod před kontrolou (odhad z mapy): %(label)s", { label: leg.attack.label }), { permanent: false }).addTo(groups.sel);
    }
    // the backstop: where a runner who ran on past the control meets it, to the left, straight on and to the right
    ((leg && leg.beyond && leg.beyond.parts) || []).forEach(function (q) {
      var tip = T("zarážka za kontrolou (odhad z mapy): %(label)s", { label: q.label });
      if (q.line.length > 1) {
        L.polyline(q.line, { className: "ob-zarazka-cara", weight: 4, opacity: 0.9, dashArray: "3 7" })
          .bindTooltip(tip, { sticky: true }).addTo(groups.sel);
      }
      L.circleMarker([q.lat, q.lon], { className: "ob-zarazka", radius: 6, weight: 3, fillOpacity: 0.9 })
        .bindTooltip(tip).addTo(groups.sel);
    });
    // where the track went through what the best route must not (a railway away from a crossing, fenced ground)
    ((leg && leg.crossed && leg.crossed.at) || []).forEach(function (p) {
      L.circleMarker(p, { className: "ob-prekroceni", radius: 10, weight: 3 })
        .bindTooltip(T("tudy vede tvoje stopa, nejlepší postup tudy nesmí")).addTo(groups.sel);
    });
    // ... and where the planned route does (it is priced without those barriers too)
    ((leg && leg.note && leg.note.plan && leg.note.plan.crossed) || []).forEach(function (p) {
      L.circleMarker(p, { className: "ob-prekroceni", radius: 10, weight: 3 })
        .bindTooltip(T("tudy vede tvůj plán, nejlepší postup tudy nesmí")).addTo(groups.sel);
    });
    catching(leg);
    Array.prototype.forEach.call(document.querySelectorAll("#legs tr[data-n]"), function (tr) {
      tr.classList.toggle("sel", Number(tr.dataset.n) === selected);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".ob-sl, .ob-mini-r"), function (b) {
      b.classList.toggle("sel", Number(b.dataset.n) === selected);
    });
    var box = $("pas-useky");
    Array.prototype.forEach.call(box.querySelectorAll("button"), function (b) {
      var on = b.dataset.n === "" ? !selected : Number(b.dataset.n) === selected;  // "" is the chip of the whole course
      b.setAttribute("aria-pressed", on ? "true" : "false");
      if (!on) { return; }
      // bring the chip into view inside the strip only: the page itself must not jump while a table is read
      var left = b.offsetLeft - box.offsetLeft;
      if (left < box.scrollLeft) {
        box.scrollLeft = left;
      } else if (left + b.offsetWidth > box.scrollLeft + box.clientWidth) {
        box.scrollLeft = left + b.offsetWidth - box.clientWidth;
      }
    });
  }
  // The layer "catching features" (a check box turns it on): small rings at every control; with a leg selected
  // only at its control, numbered and with the way to the control; where the track shows the runner was lost
  // there, the place contact was lost, the wandering that followed and the feature that was closest.
  function catching(sel) {
    groups.catch.clearLayers();
    if (!$("c-zachyt").checked) { return; }
    D.legs.forEach(function (leg) {
      var r = leg.relocate, c = D.course[leg.n], on = sel && sel.n === leg.n;
      if (!r || (sel && !on)) { return; }
      r.features.forEach(function (f, k) {
        var p = [f.lat, f.lon];
        if (on) {
          // the way to the control: straight, or round what one cannot go through (f.via); never straight through it
          L.polyline(f.via || [p, [c.lat, c.lon]], { className: "ob-zachyt-smer", weight: 2, opacity: 0.8, dashArray: "5 5", interactive: false })
            .addTo(groups.catch);
          L.marker(p, { icon: L.divIcon({ className: "ob-zachyt-cislo", html: String(k + 1), iconSize: [20, 20], iconAnchor: [10, 10] }) })
            .bindTooltip(f.where + "; " + f.back).addTo(groups.catch);
        } else {
          L.circleMarker(p, { className: "ob-zachyt", radius: 4, weight: 2, fillOpacity: 0.9 })
            .bindTooltip(leg.name + ": " + f.where).addTo(groups.catch);
        }
      });
      if (on && r.lost) {
        var walk = [], i;
        for (i = r.lost.i; i <= leg.b; i++) { walk.push([D.track.lat[i], D.track.lon[i]]); }
        L.polyline(walk, { className: "ob-bloudeni", weight: 11, opacity: 0.35, interactive: false }).addTo(groups.catch).bringToBack();
        L.circleMarker(r.lost.at, { className: "ob-kontakt", radius: 8, weight: 4, fillOpacity: 0.9 })
          .bindTooltip(T("tady jsi opustil přímý směr ke kontrole")).addTo(groups.catch);
        if (r.lost.near) {
          L.polyline([[D.track.lat[r.lost.near.i], D.track.lon[r.lost.near.i]]].concat(r.lost.near.via || [[r.lost.near.lat, r.lost.near.lon], [c.lat, c.lon]]),
            { className: "ob-bloudeni", weight: 3, opacity: 0.9, dashArray: "2 6", interactive: false }).addTo(groups.catch);
          L.circleMarker([r.lost.near.lat, r.lost.near.lon], { className: "ob-kontakt", radius: 6, weight: 3, fillOpacity: 0.9 })
            .bindTooltip(T("nejbližší záchytný bod při bloudění")).addTo(groups.catch);
        }
      }
    });
  }

  // an alternative stands out while the pointer is on its line or on its row in the panel
  function lit(k, on) {
    if (altLines[k]) { altLines[k].setStyle({ weight: on ? 6 : 3, opacity: on ? 1 : 0.6 }); }
    Array.prototype.forEach.call(document.querySelectorAll("#p-alts tr[data-alt]"), function (tr) {
      tr.classList.toggle("sel", on && Number(tr.dataset.alt) === k);
    });
  }

  // the strip over the map: one chip per leg in the order of the course, coloured by the loss
  function strip() {
    var box = $("pas-useky");
    box.textContent = "";
    var all = document.createElement("button");
    all.type = "button";
    all.className = "ob-cip";
    all.dataset.n = "";
    all.textContent = T("Celá trať");
    all.title = T("Zrušit výběr úseku a ukázat celou trať (Esc)");
    all.setAttribute("aria-pressed", selected ? "false" : "true");
    all.addEventListener("click", function () { select(null); });
    box.appendChild(all);
    D.legs.forEach(function (l) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "ob-cip z" + grade(l.loss);
      b.dataset.n = l.n;
      b.textContent = l.name;
      b.title = l.name + ": " + mmss(l.time) + (l.loss >= 20 ? ", " + T("ztráta %(t)s", { t: mmss(l.loss) }) : "") + (l.mistake ? " · " + l.mistake.label : "");
      b.setAttribute("aria-pressed", selected === l.n ? "true" : "false");
      b.addEventListener("click", function () { select(l.n); });
      box.appendChild(b);
    });
    $("pas").hidden = !D.legs.length;
  }
  // the leg before or after the selected one (the first or the last when none is selected)
  function step(d) {
    var i = D.legs.map(function (l) { return l.n; }).indexOf(selected);
    i = i < 0 ? (d > 0 ? 0 : D.legs.length - 1) : i + d;
    if (D.legs[i]) { select(D.legs[i].n); }
  }

  function totals() {
    var t = D.totals, sum = t.route + t.mistake + t.fatigue, parts = [];
    if (D.has_routes) { parts.push(T("volba postupu %(t)s", { t: mmss(t.route) })); }
    parts.push(D.has_routes ? T("chyby v provedení %(t)s", { t: mmss(t.mistake) }) : T("odhad ztráty z GPS %(t)s", { t: mmss(t.mistake) }));
    if (t.fatigue >= 1) { parts.push(T("únava %(t)s", { t: mmss(t.fatigue) })); }
    $("totals").innerHTML = T("Ztráta celkem <b>%(sum)s</b>:", { sum: mmss(sum) }) + " " + parts.join(", ") + "." +
      (t.deliberate >= 1 ? " " + T("Schválné zastávky %(t)s se jako chyba nepočítají.", { t: mmss(t.deliberate) }) : "") +
      (D.rerouting ? " <b>" + T("Zakázané přechody se změnily, postupy se přepočítávají.") + "</b>" : "");
  }

  function marks(leg) {
    var n = leg.note, m = [];
    if (leg.deliberate_s >= 1) { m.push(leg.refreshment_s >= 1 && !n.deliberate_stop ? T("občerstvení") : T("schválná zastávka")); }
    if (n.lost_contact) { m.push(T("ztráta kontaktu s mapou")); }
    if (n.green === "through") { m.push(T("zelenou proběhl")); }
    if (n.green === "around") { m.push(T("zelenou obíhal")); }
    if (n.fatigue) { m.push(T("únava %(t)s", { t: n.fatigue })); }
    if (n.planned) { m.push(n.plan ? T("plán %(t)s proti nejlepšímu", { t: mmss(n.plan.delta, true) }) : T("plán nakreslen")); }
    return m;
  }

  function table() {
    var off = D.legs.some(function (l) { return l.official !== null; }), R = D.has_routes;
    var W = D.legs.some(function (l) { return l.ws; });
    var h = "<thead><tr><th>" + T("Úsek") + "</th><th class='num'>" + T("Čas") + "</th>" + (off ? "<th class='num'>" + T("Oficiálně") + "</th>" : "") +
      (R ? "<th class='num'>" + T("Nejlepší") + "</th><th class='num'>" + T("Ztráta") + "</th><th class='num'>" + T("volbou") + "</th><th class='num'>" + T("provedením") + "</th>"
         : "<th class='num'>" + T("Odhad ztráty") + "</th>") +
      (W ? "<th class='num' title='" + T("ztráta proti tvému normálu podle mezičasů kategorie") + "'>" + T("Podle mezičasů") + "</th>" : "") +
      "<th class='num'>" + T("Stání") + "</th><th>" + T("Model") + "</th><th>" + T("Typ chyby") + "</th><th>" + T("Co se stalo") + "</th><th>" + T("Vysvětlení") + "</th></tr></thead><tbody>";
    D.legs.forEach(function (l) {
      var what = l.flags.concat(marks(l).map(function (x) { return "<b>" + x + "</b>"; }));
      h += "<tr data-n='" + l.n + "'" + (selected === l.n ? " class='sel'" : "") + ">" +  // kept up to date by mark()
        "<td><i class='sw z" + grade(l.loss) + "'></i> " + esc(l.name) + "</td>" +
        "<td class='num'>" + mmss(l.time) + "</td>" + (off ? "<td class='num'>" + mmss(l.official) + "</td>" : "") +
        (R ? "<td class='num'>" + mmss(l.best ? l.best.time : null) + "</td><td class='num'><b>" + mmss(l.loss_total, true) +
             "</b></td><td class='num'>" + (l.balanced ? "<span title='" + T("postupy jsou vyrovnané") + "'>≈</span> " : "") +
             mmss(l.loss_route, true) + "</td><td class='num'>" + mmss(l.loss_exec, true) + "</td>"
           : "<td class='num'>" + mmss(l.est_loss) + "</td>") +
        (W ? "<td class='num'>" + (l.ws ? (l.ws.mistake ? "<b class='ob-typ'>" + mmss(l.ws.loss, true) + "</b>" : mmss(l.ws.loss, true)) : "") + "</td>" : "") +
        "<td class='num'>" + (l.stop_time >= 1 ? Math.round(l.stop_time) + " s" : "") + "</td>" +
        "<td>" + (l.in_model ? "✓" : "") + "</td>" +
        "<td>" + (l.mistake ? "<span class='ob-typ'>" + esc(l.mistake.label) + "</span>" : "") + "</td>" +
        "<td class='co'>" + what.join("; ") +
        (l.note.text ? "<div class='notetext'>" + esc(l.note.text) + "</div>" : "") + "</td>" +
        "<td class='explain'>" + esc(l.explain || "") + (l.mistake ? " " + esc(l.mistake.text) : "") + "</td></tr>";
    });
    $("legs").innerHTML = h + "</tbody>";
    Array.prototype.forEach.call($("legs").querySelectorAll("tr[data-n]"), function (tr) {
      tr.addEventListener("click", function () { select(Number(tr.dataset.n), true); });
    });
  }

  // --- overview of the whole race (right column) and the bar chart of the losses ---
  function lossOf(l) { return D.has_routes ? l.loss_total : l.est_loss; }
  function metrics(box, actual, model, loss) {
    box.innerHTML = "<div><span>" + T("Skutečně") + "</span><b class='ob-cislo'>" + (actual === null ? "–" : mmss(actual)) + "</b></div>" +
      "<div class='ob-model'><span>" + T("Model") + "</span><b class='ob-cislo'>" + (model === null ? "–" : mmss(model)) + "</b></div>" +
      "<div class='ob-zt'><span>" + T("Ztráta") + "</span><b class='ob-cislo'>" + (loss === null ? "–" : mmss(loss, true)) + "</b></div>";
  }
  function overview() {
    var t = D.totals, sum = t.route + t.mistake + t.fatigue;
    metrics($("o-metriky"), D.total_time, D.has_routes ? D.total_time - sum : null, D.has_routes ? sum : t.mistake);
    $("o-pozn").textContent = D.has_routes
      ? T("Model je teoretický ideál bez zaváhání, ne čas, který by šel opravdu uběhnout. Ztráta je odhad.")
      : T("Bez mapy bez tratě nejsou nejlepší postupy. Ztráta je odhad z GPS stopy.");
    var top = D.legs.filter(function (l) { return lossOf(l) >= 20; })
      .sort(function (a, b) { return lossOf(b) - lossOf(a); }).slice(0, 3), h = "";
    if (top.length) {
      h = "<h3>" + T("Největší časové ztráty") + "</h3><ul class='ob-ztraty'>" + top.map(function (l) {
        return "<li><button type='button' data-n='" + l.n + "' class='ob-ztrata-tl'><b>" + esc(T("Úsek %(name)s", { name: l.name })) + "</b>" +
          "<span class='ob-cislo'>" + mmss(lossOf(l), true) + "</span>" +
          (l.mistake ? "<small>" + esc(l.mistake.label) + "</small>" : "") + "</button></li>";
      }).join("") + "</ul>";
    }
    $("o-ztraty").innerHTML = h;
    var rows = D.legs.map(function (l) {
      return "<button type='button' data-n='" + l.n + "' class='ob-mini-r z" + grade(lossOf(l)) + "'><span>" + esc(l.name) +
        "</span><span class='ob-cislo'>" + mmss(l.time) + "</span><span class='ob-cislo ob-zt'>" +
        (lossOf(l) >= 1 ? mmss(lossOf(l), true) : "") + "</span></button>";
    }).join("");
    $("o-useky").innerHTML = "<div class='ob-mini-h'><span>" + T("Úsek") + "</span><span>" + T("Čas") + "</span><span>" + T("Ztráta") + "</span></div>" + rows;
    Array.prototype.forEach.call($("panel-empty").querySelectorAll("button[data-n]"), function (b) {
      b.addEventListener("click", function () { select(Number(b.dataset.n)); });
    });
    bars();
  }
  function bars() {
    var max = Math.max.apply(null, D.legs.map(lossOf).concat([60])), box = $("graf-sloupce");
    $("graf-useky").hidden = !D.legs.length;
    box.innerHTML = D.legs.map(function (l) {
      var v = Math.max(0, lossOf(l));
      return "<button type='button' data-n='" + l.n + "' class='ob-sl z" + grade(v) + "' title='" + esc(l.name) + ": " + T("ztráta %(t)s", { t: mmss(v) }) +
        "' aria-label='" + esc(T("Úsek %(name)s", { name: l.name })) + ", " + T("ztráta %(t)s", { t: mmss(v) }) + "'><span class='ob-sl-v' style='height:" +
        Math.max(3, Math.round(100 * v / max)) + "%'></span><span class='ob-sl-n'>" + esc(String(l.n)) + "</span></button>";
    }).join("");
    Array.prototype.forEach.call(box.querySelectorAll("button"), function (b) {
      b.addEventListener("click", function () { select(Number(b.dataset.n)); });
    });
  }

  function current() { return D.legs.filter(function (l) { return l.n === selected; })[0]; }

  // n: the number of a leg, or null for the whole course
  function select(n, scroll) {
    if (drawing || mode) { cancel(); }
    if (n === null) {
      if (noteTimer) { saveNote(); }
      selected = null;
      try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* file: or sandboxed */ }
      map.fitBounds(whole);
      mark();
      panel();
      return;
    }
    if (!D.legs.some(function (l) { return l.n === n; })) { return; }
    if (noteTimer) { saveNote(); }  // the note being written belongs to the leg that is selected now
    selected = n;
    // the leg goes into the address, so it is still selected after the page loads again
    try { history.replaceState(null, "", "#usek-" + n); } catch (e) { /* file: or sandboxed */ }
    var leg = current(), pts = legPoints(leg).concat(leg.best_route || []);
    (leg.alts || []).forEach(function (a) { pts = pts.concat(a.route); });
    if (leg.generic && leg.generic.route) { pts = pts.concat(leg.generic.route); }
    map.fitBounds(L.latLngBounds(pts).pad(0.25), { maxZoom: 19 });
    mark();
    panel();
    if (scroll) { $("map").scrollIntoView({ behavior: "smooth", block: "nearest" }); }
  }

  function panel(typing) {
    var leg = current();
    $("panel-empty").hidden = !!leg;
    $("panel-leg").hidden = !leg;
    $("souhrn").hidden = !leg;
    if (!leg) { return; }
    $("souhrn").innerHTML = "<b>" + esc(leg.name) + "</b> · " + T("čas %(t)s", { t: mmss(leg.time) }) +
      (leg.best ? " · " + T("ztráta %(t)s", { t: mmss(leg.loss_total, true) }) : " · " + T("odhad ztráty %(t)s", { t: mmss(leg.est_loss) })) +
      (leg.mistake ? " · <span class='ob-typ'>" + esc(leg.mistake.label) + "</span>" : "");
    var n = leg.note, num = [T("čas <b>%(t)s</b>", { t: mmss(leg.time) })];
    if (leg.official !== null) { num.push(T("oficiálně %(t)s", { t: mmss(leg.official) })); }
    if (leg.best) {
      num.push(T("nejlepší postup %(t)s (%(d)s m)", { t: mmss(leg.best.time), d: Math.round(leg.best.dist) }));
      num.push(T("ztráta volbou %(t)s", { t: mmss(leg.loss_route, true) }));
      num.push(T("provedením %(t)s", { t: mmss(leg.loss_exec, true) }));
    } else {
      num.push(T("odhad ztráty %(t)s", { t: mmss(leg.est_loss) }));
    }
    num.push(T("přímka %(s)s m, běženo %(r)s m", { s: Math.round(leg.straight), r: Math.round(leg.run) }));
    if (leg.ws) {
      num.push(T("podle mezičasů kategorie %(t)s proti tvému normálu", { t: mmss(leg.ws.loss, true) }) +
               (leg.ws.mistake ? " (<b>" + T("chyba") + "</b>)" : ""));
    }
    $("p-title").textContent = T("Úsek %(name)s", { name: leg.name });
    metrics($("p-metriky"), leg.time, leg.best ? leg.best.time : null, leg.best ? leg.loss_total : leg.est_loss);
    var gps = leg.corrected ? T("Stopa úseku je opravená ručně: ztráta volbou a provedením se počítá po nakreslené čáře, z osobního modelu je úsek vyřazený.")
      : n.corrected ? T("Opravená stopa je uložená, postupy se přepočítávají.")
      : leg.gps_trouble || "";
    $("p-gps").textContent = gps;
    $("p-gps").hidden = !gps;
    $("b-gps").hidden = !n.corrected;
    $("b-oprava").textContent = n.corrected ? T("Nakreslit stopu znovu") : T("Opravit moji stopu");
    $("p-numbers").innerHTML = num.join(" · ");
    $("p-mistake").textContent = leg.mistake ? leg.mistake.label + ": " + leg.mistake.text : "";
    $("p-mistake").hidden = !leg.mistake;
    $("p-explain").textContent = leg.explain || "";
    // why the best route is the best for this runner: where an average runner would go instead
    var avg = leg.generic;
    $("p-pro-tebe").textContent = avg ? (OB_LANG === "en" && avg.text_en ? avg.text_en : avg.text_cs) : "";
    $("p-pro-tebe").className = avg && avg.differs ? "nota ob-pro-tebe" : "hint";
    $("p-pro-tebe").hidden = !avg;
    // the routes of the leg side by side, all priced by the same model: the best one, the planned one, the one
    // that was run, and the alternatives
    var alts = "", row = function (label, m, delta, attrs) {
      return "<tr" + (attrs || "") + "><td>" + label + "</td><td class='num'>" + mmss(m.time) + "</td><td class='num'>" +
        (delta === null ? "" : mmss(delta, true)) + "</td><td class='num'>" + Math.round(m.dist) + " m</td><td class='num'>" +
        Math.round(m.climb) + " m</td></tr>";
    };
    if (leg.best) {
      alts = row("<i class='sw best'></i> " + T("nejlepší"), leg.best, null);
      if (n.plan) {
        alts += row("<i class='sw plan'></i> " + T("plán"), n.plan, n.plan.delta);
      } else if (n.planned) {
        alts += "<tr><td><i class='sw plan'></i> " + T("plán") + "</td><td colspan='4'>" + (D.plans_pending ? T("počítá se…") : T("není oceněn")) + "</td></tr>";
      }
      if (leg.line) { alts += row("<i class='sw z" + grade(leg.loss) + "'></i> " + T("tvoje stopa"), leg.line, leg.line.time - leg.best.time); }
      if (avg && avg.differs) {
        alts += row("<i class='sw prumer'></i> " + T("průměrný běžec"), avg, avg.time - leg.best.time,
                    " title='" + T("nejlepší postup běžce s průměrným modelem, oceněný tvým modelem") + "'");
      }
      (leg.alts || []).forEach(function (a, k) {
        alts += row("<i class='ob-alt-cislo'>" + (k + 2) + "</i> " + T("možnost %(n)s", { n: k + 2 }), a, a.delta, " data-alt='" + k + "'");
      });
      alts = "<div class='tablewrap'><table class='ob-postupy'><thead><tr><th>" + T("Postup") + "</th><th class='num' title='" +
        T("čas podle tvého modelu rychlosti") + "'>" + T("Čas") + "</th><th class='num' title='" + T("proti nejlepšímu postupu") + "'>" +
        T("Rozdíl") + "</th><th class='num'>" + T("Délka") + "</th>" +
        "<th class='num'>" + T("Stoupání") + "</th></tr></thead><tbody>" + alts + "</tbody></table></div>" +
        "<p class='hint'>" + T("Všechny časy v tabulce počítá tvůj model rychlosti pro danou čáru, i pro tvoji stopu; naměřený čas úseku je %(t)s.", { t: mmss(leg.time) }) + "</p>";
      // the track is priced without the barriers the routes obey: why it can come out faster than the best route
      if (leg.crossed) { alts += "<p class='nota'>" + esc(leg.crossed.text) + "</p>"; }
    }
    // what the model says about the planned route, or why it does not say anything yet
    var plan = "";
    if (n.plan) {
      plan = (OB_LANG === "en" && n.plan.text_en) ? n.plan.text_en : n.plan.text;
    } else if (n.planned && !D.has_routes) {
      plan = T("Plánovaný postup půjde ocenit, až budou u závodu spočítané nejlepší postupy (chybí mapa bez tratě).");
    } else if (n.planned && D.plans_pending) {
      plan = T("Čas plánovaného postupu se počítá…");
    } else if (n.planned) {
      plan = T("Plánovaný postup se nepodařilo ocenit. Nakresli ho znovu, nebo spusť v Podkladech analýzu znovu.");
    }
    $("p-plan").textContent = plan;
    $("p-plan").hidden = !plan;
    // "if you got lost": catching features around the control of the leg, and what the track says
    var rl = leg.relocate, help = "";
    if (rl) {
      if (rl.lost) { help += "<p class='ob-typ'>" + esc(rl.lost.text) + "</p>"; }
      if (rl.features.length) {
        help += "<ol>" + rl.features.map(function (f) {
          return "<li><b>" + esc(f.where) + "</b><br>" + esc(T("ke kontrole")) + " " + esc(f.back) + "</li>";
        }).join("") + "</ol>";
      } else {
        help += "<p>" + T("Do 150 m od kontroly není na mapě nic, čeho by se dalo spolehlivě chytit (žádná cesta, voda, budova ani paseka).") + "</p>";
      }
      help += "<p class='hint'>" + T("Azimuty jsou k severu mapy (magnetické poledníky), tedy rovnou pro buzolu. Body jsou čtené z kresby mapy bez tratě a pojmenované podle mapového klíče ISOM 2017-2: cesty a jejich konce a křížení, voda, budovy, oplocenky a samostatně stojící bodové značky (kupka, jáma, výrazný strom, posed a další). Plot, který nic neuzavírá, čte aplikace jako cestu. „Vrchol“ je z výškového modelu, ne z kresby. Na mapě je zapíná volba „záchytné body“.") + "</p>";
    }
    // the control at the end of the leg (not the finish): its description, typed by hand, and the page that
    // says what to do when lost there (views/lost.py)
    var atControl = leg.n < D.course.length - 1;
    if (atControl && OB.ztraceny) {
      var desc = leg.note && leg.note.control_desc;
      help += (desc ? "<p><b>" + T("Popis kontroly:") + "</b> " + esc(desc) + "</p>" : "") +
        "<p><a class='btn btn-maly' href='" + esc(OB.ztraceny) + "#k" + leg.n + "'>" + T("Ztratil jsem se tady: co dělat") + "</a></p>";
    }
    $("p-ztrata").hidden = !rl && !(atControl && OB.ztraceny);
    $("p-ztrata-telo").innerHTML = help;
    $("p-ztrata").querySelector("summary").textContent = T("Kdyby ses ztratil") + (rl && rl.lost ? " " + T("(tady jsi bloudil)") : "");
    if (leg.balanced) {
      alts += "<p class='nota'>" + T("Postupy jsou vyrovnané: když se rychlosti v terénu posunou o 20 %, vyjde jako nejlepší jiná varianta. Ztrátu volbou postupu ber jen orientačně.") + "</p>";
    }
    // where to attack the control from (before it, on the way in) and what stops a runner who ran past it
    if (leg.relocate) {
      alts += "<p class='hint'><i class='sw nabeh'></i> " + T("Náběhový bod (odhad z mapy, ze směru nejlepšího postupu):") + " " +
        (leg.attack ? esc(leg.attack.label) : T("před kontrolou není nic, čeho se chytit")) + ".<br><i class='sw zarazka'></i> " +
        T("Zarážka (co potkáš, když kontrolu přeběhneš):") + " " +
        (leg.beyond ? esc(leg.beyond.text) : T("do 200 m za kontrolou není cesta, voda ani nic velkého, co by tě zastavilo")) +
        ".</p>";
    }
    $("p-alts").innerHTML = alts;
    Array.prototype.forEach.call(document.querySelectorAll("#p-alts tr[data-alt]"), function (tr) {
      var k = Number(tr.dataset.alt);
      tr.addEventListener("mouseenter", function () { lit(k, true); });
      tr.addEventListener("mouseleave", function () { lit(k, false); });
      tr.addEventListener("click", function () { lit(k, !tr.classList.contains("sel")); });  // a tap on a phone
    });
    $("p-flags").textContent = leg.flags.join("; ");
    $("n-stop").checked = n.deliberate_stop;
    $("n-lost").checked = n.lost_contact;
    $("n-green").value = n.green || "";
    $("n-fatigue").value = n.fatigue || "";
    if (!(typing && document.activeElement === $("n-text"))) { $("n-text").value = n.text || ""; }
    var eff = [];
    if (leg.refreshment_s >= 1) {
      eff.push(T("Zastávka u občerstvovačky (%(s)s s) se bere jako schválná automaticky.", { s: Math.round(leg.refreshment_s) }));
    } else if (leg.deliberate_s >= 1) {
      eff.push(T("Schválná zastávka: %(s)s s se nepočítá jako chyba.", { s: Math.round(leg.deliberate_s) }));
    } else if (n.deliberate_stop) {
      eff.push(T("Na úseku není žádná zastávka delší než 6 s, takže se nic neodečítá."));
    }
    if (n.lost_contact) { eff.push(T("Celá ztráta úseku se vede jako chyba, ne jako volba postupu.")); }
    if (n.fatigue >= 4 && !n.lost_contact) { eff.push(T("Ztráta provedením se vede jako únava, ne jako chyba.")); }
    else if (n.fatigue >= 1 && n.fatigue <= 3) { eff.push(T("Únava %(n)s jen popisuje, výpočet nemění.", { n: n.fatigue })); }
    if (n.green === "around") { eff.push(T("Body stopy, které GPS umístila do zelené, se do modelu nepočítají.")); }
    eff.push(leg.in_model ? T("Úsek se počítá do tvého osobního modelu rychlosti.") : T("Úsek se do osobního modelu nepočítá."));
    $("p-effect").textContent = eff.join(" ");
  }

  function saveNote(extra, leaving) {
    clearTimeout(noteTimer);
    noteTimer = null;
    var leg = current();
    if (!leg) { return; }
    var body = {
      deliberate_stop: $("n-stop").checked, lost_contact: $("n-lost").checked, green: $("n-green").value || null,
      fatigue: $("n-fatigue").value || null, text: $("n-text").value, planned: leg.note.planned
    };
    Object.keys(extra || {}).forEach(function (k) { body[k] = extra[k]; });
    // a new line (or none) is the plan from now on, also for a note saved before the answer comes back
    if (extra && "planned" in extra) { leg.note.planned = extra.planned; leg.note.plan = null; }
    $("p-saved").textContent = T("Ukládám…");
    saving++;
    guard();
    var mine = ++sent;
    api(OB.note.replace("/legs/0/", "/legs/" + leg.n + "/"), "POST", body, leaving).then(function (d) {
      if (mine < shown) { return; }  // the answer to a later save is already on the page
      shown = mine;
      update(d, true);
      if (!noteTimer) { $("p-saved").textContent = T("Uloženo."); }
    }).catch(function () { $("p-saved").textContent = T("Uložení se nepovedlo, zkus to znovu."); }).then(function () {
      saving--;
      guard();
    });
  }

  function update(d, typing) {
    if (d.legs) {
      // the answer brings the numbers of the legs; their routes do not change and stay as they were loaded
      var had = {};
      D.legs.forEach(function (l) { had[l.n] = l; });
      d.legs.forEach(function (l) {
        if (l.best_route === undefined && had[l.n]) {
          l.best_route = had[l.n].best_route;
          l.alts = had[l.n].alts;
          if (l.generic && had[l.n].generic) { l.generic.route = had[l.n].generic.route; }
        }
      });
    }
    ["legs", "totals", "refreshments", "barriers", "rerouting", "plans_pending"].forEach(function (k) {
      if (d[k] !== undefined) { D[k] = d[k]; }
    });
    // the routes are being drawn again (a forbidden line changed): load the page again when they are ready
    if (D.rerouting) { document.body.setAttribute("data-obnovit", ""); }
    draw();
    table();
    strip();
    totals();
    overview();
    panel(typing);
    watchPlans();
    document.dispatchEvent(new CustomEvent("ob-data", { detail: D }));
  }

  // A planned route is priced by the worker a few seconds after it is saved: until its numbers are there,
  // ask for the legs again. Never over a note that is being written or saved (its own answer brings them).
  function watchPlans() {
    clearTimeout(planTimer);
    planTimer = null;
    var waiting = D.has_routes && D.plans_pending &&
      D.legs.some(function (l) { return l.note.planned && !l.note.plan; });
    if (!waiting) { return; }
    planTimer = setTimeout(function () {
      if (saving || noteTimer) { watchPlans(); return; }
      fetch(OB.legs).then(function (r) { return r.json(); }).then(function (d) {
        if (saving || noteTimer) { watchPlans(); } else { update(d, true); }
      }, watchPlans);
    }, 2000);
  }

  // --- drawing a line on the map: the planned route of a leg, or a forbidden crossing ---
  function startDrawing(kind) {
    if (kind === "plan" && !current()) { return; }
    drawing = [];
    drawing.kind = kind;
    bar();
    drawLine();
  }
  function line() {
    if (drawing.kind !== "plan" && drawing.kind !== "corrected") { return drawing.slice(); }
    var leg = current(), a = D.course[leg.n - 1], b = D.course[leg.n];
    return [[a.lat, a.lon]].concat(drawing, [[b.lat, b.lon]]);
  }
  function drawLine() {
    groups.draw.clearLayers();
    var cls = drawing.kind === "plan" ? "ob-plan" : drawing.kind === "corrected" ? "ob-oprava" : "ob-zakaz";
    if (line().length > 1) { L.polyline(line(), { className: cls, weight: 4, interactive: false }).addTo(groups.draw); }
    drawing.forEach(function (p) {
      L.circleMarker(p, { className: cls, radius: 4, fillColor: "#fff", fillOpacity: 1, interactive: false }).addTo(groups.draw);
    });
  }
  function stopDrawing() {
    drawing = null;
    groups.draw.clearLayers();
    bar();
  }
  function finishDrawing() {
    if (!drawing) { return; }
    var pts = line(), kind = drawing.kind;
    cancel();
    if (kind === "plan") { saveNote({ planned: pts }); return; }
    if (kind === "corrected") { saveCorrection(pts); return; }
    if (pts.length >= 2) { api(OB.barriers, "POST", { kind: kind, line: pts }).then(update); }
  }
  // "Opravit moji stopu": the line stands for the GPS track of the leg (null: back to the GPS); the routes of the
  // race are found again, and the page loads itself again when they are ready
  function saveCorrection(pts) {
    var leg = current();
    if (!leg) { return; }
    $("p-saved").textContent = T("Ukládám…");
    api(OB.note.replace("/legs/0/note", "/legs/" + leg.n + "/oprava"), "POST", { line: pts }).then(function (d) {
      update(d, true);
      document.body.setAttribute("data-obnovit", "");
      $("p-saved").textContent = pts ? T("Opravená stopa uložená, postupy se přepočítávají.") : T("Zpět na GPS stopu, postupy se přepočítávají.");
    }).catch(function () { $("p-saved").textContent = T("Uložení se nepovedlo, zkus to znovu."); });
  }

  // "Začátek a konec GPS stopy": the part of the recording cut off (or about to be, while the sliders move) is
  // drawn grey and dashed, with a dot where the track begins and ends. Times are seconds from the first position
  // the watch wrote (oroute/gpstrim.py); the track of the page starts at trim.start_s of them.
  function trimPreview() {
    var T = D.track.trim, form = document.querySelector("[data-orez]");
    if (!T || !groups.orez) { return; }
    var raw = T.head.slice();
    D.track.t.forEach(function (t, i) { raw.push([D.track.lat[i], D.track.lon[i], t + T.start_s]); });
    raw = raw.concat(T.tail);
    function cut(lo, hi) {
      var before = [], after = [], a = null, b = null;
      groups.orez.clearLayers();
      raw.forEach(function (p) {
        if (p[2] < lo) { before.push([p[0], p[1]]); } else if (p[2] > hi) { after.push([p[0], p[1]]); }
        else { if (!a) { a = p; } b = p; }
      });
      // the dashed line reaches the first (last) point kept: the straight line the cut takes away
      if (before.length && a) { before.push([a[0], a[1]]); }
      if (after.length && b) { after.unshift([b[0], b[1]]); }
      [before, after].forEach(function (pts) {
        if (pts.length > 1) {
          L.polyline(pts, { className: "ob-gps-orez", weight: 3, interactive: false }).addTo(groups.orez);
        }
      });
      [a, b].forEach(function (p) {
        if (p && (before.length || after.length)) {
          L.circleMarker([p[0], p[1]], { className: "ob-gps-orez-bod", radius: 4, weight: 1.5, fillOpacity: 1,
                                         interactive: false }).addTo(groups.orez);
        }
      });
    }
    cut(T.start_s, T.end_s);
    if (!form) { return; }
    var lo = form.elements.start_s, hi = form.elements.end_s, box = form.querySelector("[data-orez-rucne]");
    function fmt(s) { s = Math.round(s); return Math.floor(s / 60) + ":" + ("0" + s % 60).slice(-2); }
    function show() {
      var mode = form.elements.mode.value;
      box.hidden = mode !== "manual";
      if (+lo.value > +hi.value - 60) {
        if (document.activeElement === hi) { hi.value = +lo.value + 60; } else { lo.value = Math.max(0, +hi.value - 60); }
      }
      form.querySelectorAll("[data-orez-cas]")[0].textContent = fmt(lo.value);
      form.querySelectorAll("[data-orez-cas]")[1].textContent = fmt(hi.value);
      if (mode === "manual") { cut(+lo.value, +hi.value); }
      else if (mode === "off") { cut(-1, T.length_s + 1); }
      else { cut(T.auto.start_s, T.auto.end_s); }
    }
    form.addEventListener("input", show);
    form.addEventListener("change", show);
  }
})();
