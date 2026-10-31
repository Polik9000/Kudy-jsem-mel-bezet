/* Placing a photo of the map by hand (views/photo.py): pick a control in the list, click (tap) the centre of its
   circle on the photo. From the 4th point the server says how far each point is from where the others put it,
   what is wrong, and where the runner's track lies on the photo. Markers can be dragged; × removes a point. */
(function () {
  "use strict";
  var OB = window.OB, $ = function (id) { return document.getElementById(id); };
  var W = OB.size[0], H = OB.size[1];
  var points = {};          // control name -> [u, v] in pixels of the photo
  var markers = {};
  var deviation = {};       // control name -> metres, from the last check
  var selected = null, track = null, sent = 0, shown = 0;
  OB.points.forEach(function (p) { points[p[0]] = [p[1], p[2]]; });

  var map = L.map("foto-mapa", { crs: L.CRS.Simple, minZoom: -5, maxZoom: 3, zoomSnap: 0.25, attributionControl: false });
  // picture pixel (u, v) <-> map (lat, lng) = (-v, u)
  var ll = function (u, v) { return L.latLng(-v, u); };
  var bounds = L.latLngBounds(ll(0, H), ll(W, 0));
  L.imageOverlay(OB.photo, bounds).addTo(map);
  map.fitBounds(bounds);
  OB.map = map;                 // for a scripted walk through the page (tools/shots-foto.json)
  map.setMaxBounds(bounds.pad(0.25));

  function esc(t) {
    return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
  function label(name) { return name === "S" ? "Start" : name === "C" ? "Cíl" : "Kontrola " + name; }
  function count() { return Object.keys(points).length; }
  function nextFree(after) {
    var names = OB.names.filter(function (n) { return n[1]; }).map(function (n) { return n[0]; });
    var i = names.indexOf(after);
    for (var k = 1; k <= names.length; k++) {
      var n = names[(i + k) % names.length];
      if (!points[n]) { return n; }
    }
    return null;
  }

  function icon(name) {
    var d = deviation[name], bad = d !== undefined && d !== null && d > 40;
    return L.divIcon({ className: "ob-foto-bod" + (bad ? " spatne" : "") + (name === selected ? " vybrany" : ""),
                       html: "<span>" + esc(name) + "</span>", iconSize: [28, 28], iconAnchor: [14, 14] });
  }
  function place(name) {
    var p = points[name];
    if (!p) {
      if (markers[name]) { map.removeLayer(markers[name]); delete markers[name]; }
      return;
    }
    if (!markers[name]) {
      markers[name] = L.marker(ll(p[0], p[1]), { icon: icon(name), draggable: true, keyboard: false,
                                                  title: label(name) }).addTo(map);
      markers[name].on("dragend", function (ev) {
        var q = ev.target.getLatLng();
        points[name] = [q.lng, -q.lat];
        check();
      });
      markers[name].on("click", function () { select(name); });
    } else {
      markers[name].setLatLng(ll(p[0], p[1]));
    }
    markers[name].setIcon(icon(name));
  }

  function list() {
    var html = OB.names.map(function (n) {
      var name = n[0], p = points[name], d = deviation[name];
      var cls = (name === selected ? "vybrany " : "") + (p ? "je" : "") + (d !== undefined && d !== null && d > 40 ? " spatne" : "");
      var dev = p ? (d === undefined || d === null ? "✓" : "± " + d + " m") : (n[1] ? "" : "bez ražení");
      return "<li class=\"" + cls + "\"><button type=\"button\" data-bod=\"" + esc(name) + "\"" + (n[1] ? "" : " disabled") +
             " aria-pressed=\"" + (name === selected) + "\"><b>" + esc(name) + "</b> <small>" + esc(dev) + "</small></button>" +
             (p ? "<button type=\"button\" class=\"smazat\" data-smazat=\"" + esc(name) + "\" aria-label=\"Smazat bod " +
                  esc(label(name)) + "\">×</button>" : "") + "</li>";
    }).join("");
    $("foto-seznam").innerHTML = html;
    $("foto-vyber").textContent = selected ? "Klikni na fotce: " + label(selected) + "." :
      "Vyber v seznamu kontrolu, kterou chceš označit.";
  }
  function select(name) {
    selected = name;
    Object.keys(markers).forEach(place);
    list();
  }

  $("foto-seznam").addEventListener("click", function (ev) {
    var b = ev.target.closest("button");
    if (!b) { return; }
    if (b.dataset.smazat) {
      delete points[b.dataset.smazat];
      delete deviation[b.dataset.smazat];
      place(b.dataset.smazat);
      check();
      return;
    }
    select(b.dataset.bod);
  });
  map.on("click", function (ev) {
    if (!selected) { return; }
    var u = ev.latlng.lng, v = -ev.latlng.lat;
    if (u < 0 || v < 0 || u > W || v > H) { return; }
    var name = selected;
    points[name] = [u, v];
    place(name);
    selected = nextFree(name);
    Object.keys(markers).forEach(place);
    check();
  });
  $("foto-stopa").addEventListener("change", drawTrack);

  function drawTrack() {
    if (track) { map.removeLayer(track); track = null; }
    if ($("foto-stopa").checked && OB.track) {
      track = L.polyline(OB.track.map(function (p) { return ll(p[0], p[1]); }),
                         { className: "ob-foto-stopa", interactive: false }).addTo(map);
    }
  }

  function check() {
    var mine = ++sent;
    var body = { points: Object.keys(points).map(function (k) { return { control: k, u: points[k][0], v: points[k][1] }; }) };
    list();
    fetch(OB.check, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": OB.csrf },
                      body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) { throw new Error("HTTP " + r.status); } return r.json(); })
      .then(function (d) {
        if (mine < shown) { return; }
        shown = mine;
        deviation = d.deviation || {};
        OB.track = d.track || null;
        drawTrack();
        var n = count(), msg = [];
        if (n < OB.minPoints) {
          msg.push("Označeno " + n + " z aspoň " + OB.minPoints + " bodů.");
        } else if (d.ok) {
          msg.push(d.summary || ("Usazení vychází s odchylkou " + Math.round(d.rms) + " m, přesnost asi ±" + d.accuracy + " m."));
        }
        (d.problems || []).forEach(function (p) { if (n >= OB.minPoints || p.indexOf("dvakrát") >= 0) { msg.push(p); } });
        $("foto-stav").innerHTML = msg.map(function (m) { return "<p>" + esc(m) + "</p>"; }).join("");
        $("foto-stav").className = "ob-foto-stav" + (d.ok ? " ok" : (n >= OB.minPoints ? " chyba" : ""));
        $("foto-ulozit").disabled = !d.ok;
        Object.keys(markers).forEach(place);
        list();
      })
      .catch(function () {
        $("foto-stav").innerHTML = "<p>Spojení se serverem selhalo, zkus bod posunout znovu.</p>";
      });
  }

  Object.keys(points).forEach(place);
  selected = nextFree("C");
  list();
  if (count()) { check(); }
}());
