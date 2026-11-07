/* Shared behaviour of every page: light/dark switch, clock, header height, menu, job counter, table sorting.
   The light/dark mode is kept under the application-specific "ob-rezim" key. */
(function () {
  "use strict";
  var root = document.documentElement;

  /* The texts the scripts show are written in Czech; in an English page window.OBAPP.t maps them to English
     (webapp/lang_en.py EN_JS). A call with a second argument, {n: 3}, fills the %(n)s places of the text. */
  var DICT = (window.OBAPP && window.OBAPP.t) || {};
  window.obT = function (text, vars) {
    var s = Object.prototype.hasOwnProperty.call(DICT, text) ? DICT[text] : text;
    return vars ? s.replace(/%\((\w+)\)s/g, function (all, k) { return k in vars ? vars[k] : all; }) : s;
  };
  var t = window.obT;

  // light / dark: no value = follow the device
  // drawn icons, not the characters ◐ ☀ ☾: some systems have no font with them and show a dot
  var SVG = function (body) {
    return "<svg viewBox='0 0 16 16' width='14' height='14' aria-hidden='true' fill='none' stroke='currentColor' " +
      "stroke-width='1.6' stroke-linecap='round'>" + body + "</svg>";
  };
  var btn = document.getElementById("rezim"), SIGN = {
    "": SVG("<circle cx='8' cy='8' r='6'/><path d='M8 2a6 6 0 0 1 0 12z' fill='currentColor' stroke='none'/>"),
    svetly: SVG("<circle cx='8' cy='8' r='3'/><path d='M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.4 1.4M11.6 11.6 13 13M3 13l1.4-1.4M11.6 4.4 13 3'/>"),
    tmavy: SVG("<path d='M13 10A6 6 0 0 1 6 3a6 6 0 1 0 7 7z' fill='currentColor' stroke='none'/>")
  };
  var KEY = "ob-rezim";
  function mode() {
    try {
      var m = localStorage.getItem(KEY);
      return m || "";
    } catch (e) { return ""; }
  }
  function show(m) {
    if (m) { root.setAttribute("data-theme", m); } else { root.removeAttribute("data-theme"); }
    btn.innerHTML = SIGN[m] || SIGN[""];
    btn.title = m === "svetly" ? t("Světlý režim") : m === "tmavy" ? t("Tmavý režim") : t("Režim podle zařízení");
  }
  if (btn) {
    btn.hidden = false;
    show(mode());
    btn.addEventListener("click", function () {
      var next = { "": "svetly", svetly: "tmavy", tmavy: "" }[mode()] || "";
      try { localStorage.setItem(KEY, next); } catch (e) { /* private mode */ }
      show(next);
      document.dispatchEvent(new CustomEvent("ob-rezim"));
    });
  }

  // clock in the header
  var clock = document.getElementById("ted-cas");
  function tick() {
    var d = new Date(), p = function (n) { return ("0" + n).slice(-2); };
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var day = window.OBAPP && window.OBAPP.lang === "en" ? d.getDate() + " " + months[d.getMonth()] + " " + d.getFullYear()
      : d.getDate() + ". " + (d.getMonth() + 1) + ". " + d.getFullYear();
    clock.textContent = day + " " + p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
  }
  if (clock) { tick(); setInterval(tick, 1000); }

  // the sticky left menu sits under the header: tell the stylesheet how tall the header really is
  var head = document.querySelector(".sitehead");
  function headHeight() { if (head) { root.style.setProperty("--vyska-hlavicky", head.offsetHeight + "px"); } }
  headHeight();
  window.addEventListener("resize", headHeight);

  // a click outside the open menu closes it
  document.addEventListener("click", function (ev) {
    Array.prototype.forEach.call(document.querySelectorAll("details.menu[open]"), function (m) {
      if (!m.contains(ev.target)) { m.removeAttribute("open"); }
    });
  });

  // While something is being computed: show how many jobs are left. A page that shows the state of the jobs
  // (<body data-obnovit>) loads itself again when they finish, but never over work in progress: a chosen
  // file, a form that is being filled in, or whatever the page guards itself (data-no-reload). Then it waits.
  var jobs = window.OBAPP && window.OBAPP.jobs, badges = document.querySelectorAll(".ob-ulohy"), was = 0, due = false;
  function unsaved() {
    var fields = document.querySelectorAll("form[method=post] input, form[method=post] select, form[method=post] textarea");
    return Array.prototype.some.call(fields, function (el) {
      if (el.type === "hidden") { return false; }
      if (el.type === "file") { return el.files.length > 0; }
      if (el.type === "checkbox" || el.type === "radio") { return el.checked !== el.defaultChecked; }
      if (el.tagName === "SELECT") {
        var first = 0;  // a list without a marked option starts on its first one
        Array.prototype.some.call(el.options, function (o, i) { if (o.defaultSelected) { first = i; } return o.defaultSelected; });
        return el.selectedIndex !== first;
      }
      return el.value !== el.defaultValue;
    });
  }
  var timer = null;
  function next(ms) { clearTimeout(timer); timer = setTimeout(poll, ms); }
  function poll() {
    if (document.hidden) { return; }  // nobody is looking: asked again when the tab comes back (below)
    var body = document.body, race = body.dataset.zavod, line = document.getElementById("ob-prubeh");
    fetch(jobs + (race ? "?entry=" + race : "")).then(function (r) { return r.json(); }).then(function (d) {
      Array.prototype.forEach.call(badges, function (b) { b.hidden = !d.active; b.textContent = d.active; });
      // how far the running jobs are: in the job list and on the page of the race that is being analysed
      (d.running || []).forEach(function (j) {
        var cell = document.querySelector('[data-uloha="' + j.id + '"]');
        if (cell && j.message) { cell.textContent = j.message; }
        if (!cell && document.querySelector("[data-ulohy]")) { due = true; }  // the list still shows it waiting
      });
      if (line && d.progress) { line.textContent = d.progress; }
      if (line && d.progress === "") { due = true; }  // the job of the race ended, also when it failed
      // the analysis the page shows was replaced: the track is ready before the routes, show it right away
      var replaced = d.analysis !== undefined && d.analysis !== body.dataset.analyza;
      if (((was && !d.active) || replaced) && body.hasAttribute("data-obnovit")) { due = true; }
      if (due && !body.dataset.noReload && !unsaved()) { location.reload(); return; }
      was = d.active;
      next(d.active || due ? 3000 : 20000);
    }).catch(function () { next(20000); });
  }
  if (jobs) {
    poll();
    document.addEventListener("visibilitychange", function () { if (!document.hidden) { next(0); } });
  }

  // A form with files (<form data-nahravani>) is sent by script, so the page can say how much is uploaded:
  // a whole Garmin export or a map takes a while. The server answers with the address to go to (views.go).
  Array.prototype.forEach.call(document.querySelectorAll("form[data-nahravani]"), function (form) {
    var note = form.querySelector(".ob-nahravani-stav"), button = form.querySelector("button[type=submit]");
    form.addEventListener("submit", function (ev) {
      if (!window.FormData || !window.XMLHttpRequest) { return; }
      ev.preventDefault();
      var bar = form.querySelector("progress") || document.createElement("progress"), xhr = new XMLHttpRequest();
      bar.max = 100;
      bar.value = 0;
      if (note) { note.textContent = t("Nahrávám…") + " "; note.appendChild(bar); }
      button.disabled = true;
      function failed(text) {
        if (note) { note.textContent = text; }
        button.disabled = false;
      }
      xhr.upload.addEventListener("progress", function (e) {
        if (!e.lengthComputable) { return; }
        bar.value = 100 * e.loaded / e.total;
        if (note) {
          note.firstChild.textContent = e.loaded < e.total ? t("Nahrávám…") + " " + Math.round(bar.value) + " % "
            : t("Nahráno, server soubory ukládá…") + " ";
        }
      });
      xhr.addEventListener("load", function () {
        var to = null;
        try { to = JSON.parse(xhr.responseText).redirect; } catch (e) { /* an error page, not our answer */ }
        if (xhr.status !== 200 || !to) {
          failed(xhr.status === 413 ? t("Soubor je větší, než server přijme.") : t("Nahrání se nepovedlo (HTTP %(status)s). Zkus to znovu.", { status: xhr.status }));
          return;
        }
        form.reset();  // nothing is left unsaved, the page may go on
        var here = location.href.split("#")[0], there = new URL(to, location.href);
        location.href = there.href;
        if (there.href.split("#")[0] === here) { location.reload(); }  // only the part after # changed
      });
      xhr.addEventListener("error", function () { failed(t("Nahrání se nepovedlo (spojení se přerušilo). Zkus to znovu.")); });
      xhr.open("POST", form.getAttribute("action") || location.href);
      xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
      xhr.send(new FormData(form));
    });
  });

  // Files can be dropped on a file field of such a form (<form data-pretahni>): on its whole label, not only
  // on the small button of the browser.
  Array.prototype.forEach.call(document.querySelectorAll("form[data-pretahni] label"), function (label) {
    var input = label.querySelector("input[type=file]");
    if (!input) { return; }
    function over(ev, on) {
      ev.preventDefault();
      label.classList.toggle("ob-pretahuje", on);
    }
    label.addEventListener("dragover", function (ev) { over(ev, true); });
    label.addEventListener("dragleave", function (ev) { over(ev, false); });
    label.addEventListener("drop", function (ev) {
      over(ev, false);
      var ok = (input.accept || "").split(",").map(function (x) { return x.trim().toLowerCase(); }).filter(Boolean);
      var files = Array.prototype.filter.call(ev.dataTransfer.files, function (f) {
        return !ok.length || ok.some(function (ext) { return f.name.toLowerCase().slice(-ext.length) === ext; });
      });
      if (!files.length) { return; }
      try {
        var dt = new DataTransfer();
        (input.multiple ? files : files.slice(0, 1)).forEach(function (f) { dt.items.add(f); });
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      } catch (e) { /* an old browser: the button of the field still works */ }
    });
  });

  // sortable tables: <th data-sort="text|number">, the cell value in data-value or its text
  function cellValue(tr, i, numeric) {
    var td = tr.children[i], v = td ? (td.dataset.value !== undefined ? td.dataset.value : td.textContent.trim()) : "";
    if (!numeric) { return v.toLocaleLowerCase("cs"); }
    v = parseFloat(String(v).replace(",", "."));
    return isNaN(v) ? Infinity : v;
  }
  Array.prototype.forEach.call(document.querySelectorAll("th[data-sort]"), function (th) {
    // also from the keyboard: Tab to the heading, Enter or Space sorts
    th.tabIndex = 0;
    th.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); th.click(); }
    });
    th.addEventListener("click", function () {
      var table = th.closest("table"), body = table.tBodies[0], i = Array.prototype.indexOf.call(th.parentNode.children, th);
      var numeric = th.dataset.sort === "number", asc = th.getAttribute("aria-sort") !== "ascending";
      Array.prototype.forEach.call(th.parentNode.children, function (o) { o.removeAttribute("aria-sort"); });
      th.setAttribute("aria-sort", asc ? "ascending" : "descending");
      var rows = Array.prototype.slice.call(body.rows);
      rows.sort(function (a, b) {
        var x = cellValue(a, i, numeric), y = cellValue(b, i, numeric);
        return (x < y ? -1 : x > y ? 1 : 0) * (asc ? 1 : -1);
      });
      rows.forEach(function (r) {
        Array.prototype.forEach.call(r.cells, function (c, k) { c.classList.toggle("sortcol", k === i); });
        body.appendChild(r);
      });
    });
  });

  // search box that filters the rows of a table: <input type="search" data-filter="#table-id">
  Array.prototype.forEach.call(document.querySelectorAll("input[data-filter]"), function (inp) {
    var table = document.querySelector(inp.dataset.filter);
    if (!table) { return; }
    inp.addEventListener("input", function () {
      var q = inp.value.trim().toLocaleLowerCase("cs");
      Array.prototype.forEach.call(table.tBodies[0].rows, function (r) {
        r.hidden = !!q && r.textContent.toLocaleLowerCase("cs").indexOf(q) < 0;
      });
    });
  });

  // tabs: <div data-taby><nav class="taby"><a class="tab" href="#id">…</a></nav><section class="tabpanel" id="id">…
  Array.prototype.forEach.call(document.querySelectorAll("[data-taby]"), function (box) {
    var tabs = box.querySelectorAll(".taby .tab"), panels = box.querySelectorAll(".tabpanel");
    if (!tabs.length) { return; }
    box.classList.add("js-taby");
    function show(id) {
      Array.prototype.forEach.call(tabs, function (t) {
        var on = t.getAttribute("href") === "#" + id;
        t.classList.toggle("aktivni", on);
        if (on) { t.setAttribute("aria-current", "true"); } else { t.removeAttribute("aria-current"); }
      });
      Array.prototype.forEach.call(panels, function (p) { p.classList.toggle("aktivni", p.id === id); });
      document.dispatchEvent(new CustomEvent("ob-tab", { detail: id }));
    }
    Array.prototype.forEach.call(tabs, function (t) {
      t.addEventListener("click", function (ev) {
        ev.preventDefault();
        var id = t.getAttribute("href").slice(1);
        show(id);
        try { history.replaceState(null, "", "#" + id); } catch (e) { /* file: or sandboxed */ }
      });
    });
    document.addEventListener("ob-tab-show", function (ev) { show(ev.detail); });
    // <a data-tab="id"> anywhere on the page opens that tab
    Array.prototype.forEach.call(document.querySelectorAll("a[data-tab]"), function (a) {
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        show(a.dataset.tab);
        try { history.replaceState(null, "", "#" + a.dataset.tab); } catch (e) { /* file: or sandboxed */ }
        box.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
    // the tab named in the address, else the one the page asks for (data-vychozi), else the first
    var wanted = location.hash.slice(1), first = box.dataset.vychozi || tabs[0].getAttribute("href").slice(1);
    show(wanted && box.querySelector(".tabpanel#" + CSS.escape(wanted)) ? wanted : first);
  });

  // the split-time graph (services/charts.splits_chart): the runner under the pointer or the finger, with the loss
  // on the reference at the nearest control; the line is highlighted
  Array.prototype.forEach.call(document.querySelectorAll("[data-mezicasy]"), function (box) {
    var svg = box.querySelector("svg"), tip = box.querySelector(".ob-graf-tip"), lit = null;
    if (!svg || !tip) { return; }
    function mmss(s) {
      var a = Math.abs(Math.round(s)), sec = a % 60;
      return Math.floor(a / 60) + ":" + (sec < 10 ? "0" : "") + sec;
    }
    function hide() {
      tip.hidden = true;
      if (lit) { lit.classList.remove("zvyrazneno"); lit = null; }
    }
    function show(hit, ev) {
      var line = hit.previousElementSibling;
      if (lit !== line) {
        if (lit) { lit.classList.remove("zvyrazneno"); }
        lit = line;
        line.classList.add("zvyrazneno");
        line.parentNode.appendChild(line);          // on top of the others, its hit line after it again
        line.parentNode.appendChild(hit);
      }
      var pt = svg.createSVGPoint();
      pt.x = ev.clientX; pt.y = ev.clientY;
      var x = pt.matrixTransform(svg.getScreenCTM().inverse()).x;
      var body = hit.getAttribute("data-body").split(";"), best = 0, gap = Infinity;
      body.forEach(function (b, i) {
        var d = Math.abs(parseFloat(b) - x);
        if (d < gap) { gap = d; best = i; }
      });
      var loss = parseFloat(body[best].split(",")[1]);
      var where = best === body.length - 1 ? t("v cíli") : t("na kontrole %(n)s", { n: best + 1 });
      tip.textContent = hit.getAttribute("data-jmeno") + " " + where + ": " +
        (loss >= 0 ? t("ztráta %(t)s na referenci", { t: mmss(loss) }) : t("%(t)s před referencí", { t: mmss(loss) }));
      tip.hidden = false;
      var r = box.getBoundingClientRect();
      tip.style.left = box.scrollLeft + Math.max(0, Math.min(ev.clientX - r.left + 12, r.width - tip.offsetWidth)) + "px";
      tip.style.top = Math.max(0, ev.clientY - r.top - tip.offsetHeight - 10) + "px";
    }
    svg.addEventListener("pointermove", function (ev) {
      if (ev.target.classList.contains("zasah")) { show(ev.target, ev); }
      else if (ev.pointerType === "mouse") { hide(); }
    });
    svg.addEventListener("click", function (ev) {        // a tap on a phone
      if (ev.target.classList.contains("zasah")) { show(ev.target, ev); } else { hide(); }
    });
    svg.addEventListener("pointerleave", function (ev) { if (ev.pointerType === "mouse") { hide(); } });
  });

  window.addEventListener("error", function (e) { (window.__errors = window.__errors || []).push(String(e.message)); });

  // the app window (desktop app): a link to another site opens in the system browser, the window stays on the app
  if (window.OBAPP && window.OBAPP.external) {
    document.addEventListener("click", function (e) {
      var a = e.target.closest ? e.target.closest("a[href]") : null;
      if (!a || e.defaultPrevented || !/^https?:$/.test(a.protocol) || a.origin === location.origin) { return; }
      e.preventDefault();
      fetch(window.OBAPP.external, {
        method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": window.OBAPP.csrf },
        body: JSON.stringify({ url: a.href })
      });
    });
  }
})();
