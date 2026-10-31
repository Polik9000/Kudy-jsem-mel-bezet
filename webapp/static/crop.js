/* Cutting out the map on a Livelox screenshot by hand (views/photo.py, screen_crop.html): a rectangle over the
   screenshot whose four corners can be dragged (mouse or finger); the form sends it in pixels of the screenshot. */
(function () {
  "use strict";
  var OB = window.OB, $ = function (id) { return document.getElementById(id); };
  var W = OB.size[0], H = OB.size[1];
  var box = OB.box.slice();          // x0, y0, x1, y1 in pixels of the screenshot

  var map = L.map("foto-mapa", { crs: L.CRS.Simple, minZoom: -6, maxZoom: 2, zoomSnap: 0.25, attributionControl: false });
  // picture pixel (u, v) <-> map (lat, lng) = (-v, u)
  var ll = function (u, v) { return L.latLng(-v, u); };
  var bounds = L.latLngBounds(ll(0, H), ll(W, 0));
  L.imageOverlay(OB.photo, bounds).addTo(map);
  map.fitBounds(bounds);
  map.setMaxBounds(bounds.pad(0.25));
  OB.map = map;                       // for a scripted walk through the page (tools/pruchod_snimky.py)

  var rect = L.rectangle(L.latLngBounds(ll(box[0], box[3]), ll(box[2], box[1])),
                         { className: "ob-orez", weight: 3, fill: true, fillOpacity: 0.08, interactive: false }).addTo(map);
  var corners = [[0, 1], [2, 1], [2, 3], [0, 3]];   // which of box are x and y of each corner
  var handles = corners.map(function (c, i) {
    var m = L.marker(ll(box[c[0]], box[c[1]]), {
      draggable: true, keyboard: false, title: "Roh obdélníku",
      icon: L.divIcon({ className: "ob-foto-bod ob-orez-roh", html: "<span>" + "↖↗↘↙"[i] + "</span>",
                        iconSize: [28, 28], iconAnchor: [14, 14] })
    }).addTo(map);
    m.on("drag", function (ev) {
      var q = ev.target.getLatLng();
      box[c[0]] = Math.min(Math.max(q.lng, 0), W);
      box[c[1]] = Math.min(Math.max(-q.lat, 0), H);
      update(i);
    });
    return m;
  });

  function update(skip) {
    var x0 = Math.min(box[0], box[2]), x1 = Math.max(box[0], box[2]);
    var y0 = Math.min(box[1], box[3]), y1 = Math.max(box[1], box[3]);
    rect.setBounds(L.latLngBounds(ll(x0, y1), ll(x1, y0)));
    handles.forEach(function (m, i) {
      if (i !== skip) { m.setLatLng(ll(box[corners[i][0]], box[corners[i][1]])); }
    });
    ["x0", "y0", "x1", "y1"].forEach(function (k, i) { $("orez-" + k).value = Math.round([x0, y0, x1, y1][i]); });
    $("orez-stav").textContent = "Mapa: " + Math.round(x1 - x0) + " × " + Math.round(y1 - y0) + " px ze snímku "
      + W + " × " + H + " px.";
  }
  $("orez-cely").addEventListener("click", function () { box = [0, 0, W, H]; update(-1); });
  OB.setBox = function (b) { box = b.slice(); update(-1); };      // for the scripted walk
  update(-1);
})();
