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
  // The mode is kept with the account (POST to OBAPP.rezim) and comes back in <html data-rezim>: the app on one's
  // own computer starts on another port each time, and localStorage belongs to the address with the port.
  // localStorage stays as a copy for the pages without an account (the login).
  var KEY = "ob-rezim", saveUrl = window.OBAPP && window.OBAPP.rezim, saved = root.getAttribute("data-rezim");
  function copy() {
    try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; }
  }
  function mode() { return saved !== null ? saved : copy(); }
  function keep(m) {
    try { localStorage.setItem(KEY, m); } catch (e) { /* private mode */ }
    if (!saveUrl) { return; }
    saved = m;
    root.setAttribute("data-rezim", m);
    fetch(saveUrl, {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": window.OBAPP.csrf },
      body: JSON.stringify({ rezim: m })
    }).catch(function () { /* the next switch tries again */ });
  }
  if (saved === null && saveUrl && copy()) { keep(copy()); }  // chosen before it was kept with the account
  else if (saved !== null && saved !== copy()) { try { localStorage.setItem(KEY, saved); } catch (e) { /* private mode */ } }
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
      keep(next);
      show(next);
      document.dispatchEvent(new CustomEvent("ob-rezim"));
    });
  }

  // the same choice as three buttons on the profile page (<div data-rezim-volby>)
  var volby = document.querySelector("[data-rezim-volby]");
  if (volby && btn) {
    var choices = volby.querySelectorAll("[data-rezim-volba]");
    var markChoice = function () {
      Array.prototype.forEach.call(choices, function (b) {
        b.setAttribute("aria-pressed", b.getAttribute("data-rezim-volba") === mode() ? "true" : "false");
      });
    };
    Array.prototype.forEach.call(choices, function (b) {
      b.addEventListener("click", function () {
        var m = b.getAttribute("data-rezim-volba");
        keep(m);
        show(m);
        document.dispatchEvent(new CustomEvent("ob-rezim"));
      });
    });
    document.addEventListener("ob-rezim", markChoice);
    volby.hidden = false;
    markChoice();
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
    var fields = document.querySelectorAll("form[method=post] input, form[method=post] select, form[method=post] textarea, " +
                                           "input[form], select[form], textarea[form]");
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
      if (line && d.progress) {  // the bar fixed at the bottom (race.html): it covers nothing and moves nothing
        line.textContent = d.progress;
        line.classList.remove("ob-prubeh-konec");
        line.hidden = false;
        body.classList.add("ob-pocita");
      }
      // the job of the race ended, also when it failed (the bar is in every race page, shown only while a job runs)
      if (line && !line.hidden && !line.classList.contains("ob-prubeh-konec") && d.progress === "") { due = true; }
      // the analysis the page shows was replaced: the track is ready before the routes, show it right away
      var replaced = d.analysis !== undefined && d.analysis !== body.dataset.analyza;
      if (((was && !d.active) || replaced) && body.hasAttribute("data-obnovit")) { due = true; }
      // a job the page shows as waiting or running (data-ceka-na="job id") has ended, also before the first look
      Array.prototype.forEach.call(document.querySelectorAll("[data-ceka-na]"), function (el) {
        if ((d.ids || []).indexOf(+el.getAttribute("data-ceka-na")) < 0) { due = true; }
      });
      if (due && !body.dataset.noReload && !unsaved()) { keepPlace(); location.reload(); return; }
      was = d.active;
      next(d.active || due ? 3000 : 20000);
    }).catch(function () { next(20000); });
  }
  var bar = document.getElementById("ob-prubeh");
  if (bar && !bar.hidden) { document.body.classList.add("ob-pocita"); }  // room under the page for the bar

  // Where the reader is, kept over that reload: the open tab and the element at the top of the window, in the
  // sessionStorage of this tab only (without it nothing happens). The page may come back taller or shorter above
  // that element (a note goes away, the map loads its data): the element goes back to the same place in the window.
  var PLACE = "ob-pozice";
  function here() { return location.pathname + location.search; }
  function headBottom() { return head ? Math.max(0, head.getBoundingClientRect().bottom) : 0; }
  function anchor() {
    var top = headBottom(), below = null, over = null;
    Array.prototype.forEach.call(document.querySelectorAll("main [id]"), function (el) {
      if (el.id === "ob-prubeh") { return; }
      var r = el.getBoundingClientRect();
      if (r.height <= 0) { return; }
      if (r.top >= top) { if (!below || r.top < below.top) { below = { id: el.id, top: r.top }; } }
      else if (r.bottom > top && (!over || r.top > over.top)) { over = { id: el.id, top: r.top }; }
    });
    // the nearest element that starts in the window, else the one the top of the window is in
    return below && (!over || below.top - top < window.innerHeight / 2) ? below : over;
  }
  function keepPlace() {
    try {
      var tab = document.querySelector(".tabpanel.aktivni"), a = anchor();
      sessionStorage.setItem(PLACE, JSON.stringify({ path: here(), y: window.scrollY, tab: tab ? tab.id : null,
                                                     id: a && a.id, top: a && a.top }));
      history.scrollRestoration = "manual";
    } catch (e) { /* no storage: the page loads at the place the browser picks */ }
  }

  if (jobs) {
    poll();
    document.addEventListener("visibilitychange", function () { if (!document.hidden) { next(0); } });
  }

  // A form with files (<form data-nahravani>) is sent by script, so the page can say how much is uploaded:
  // a whole Garmin export or a map takes a while. The server answers with the address to go to (views.go).
  Array.prototype.forEach.call(document.querySelectorAll("form[data-nahravani]"), function (form) {
    // the fields, the button and the note may sit outside the form element itself (form="id", race.html)
    var note = form.querySelector(".ob-nahravani-stav") || (form.id && document.querySelector('.ob-nahravani-stav[data-form="' + form.id + '"]'));
    var button = form.querySelector("button[type=submit]") || (form.id && document.querySelector('button[type=submit][form="' + form.id + '"]'));
    form.addEventListener("submit", function (ev) {
      if (!window.FormData || !window.XMLHttpRequest) { return; }
      ev.preventDefault();
      var data = upload(form);
      if (!data) {
        if (note) { note.textContent = t("Žádný soubor se nenahrál: všechny jsou větší, než server přijme."); }
        return;
      }
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
      xhr.send(data);
    });
  });

  // What the form sends: a file larger than its field takes (data-max) is left out, and so are the largest ones
  // until all of them fit into what the server takes at once (OBAPP.maxUpload), so that one file too large does not
  // stop the others (issue 6). The names left out go along ("vynechano": "name|limit"), the server says so on the
  // next page. null when there were files and none of them can go.
  function upload(form) {
    var data = new FormData(form), whole = (window.OBAPP && window.OBAPP.maxUpload) || 0, keep = [], had = 0;
    var room = whole ? whole - 256 * 1024 : 0;       // the other fields and the parts of the form take a little
    Array.prototype.filter.call(form.elements, function (el) { return el.type === "file" && el.name; }).forEach(function (el) {
      var max = parseInt(el.getAttribute("data-max") || "0", 10);
      data.delete(el.name);
      Array.prototype.forEach.call(el.files || [], function (f) {
        had += 1;
        if (max && f.size > max) {
          data.append("vynechano", f.name + "|" + max);
        } else {
          keep.push([el.name, f]);
        }
      });
    });
    keep.sort(function (a, b) { return a[1].size - b[1].size; });
    var used = 0;
    keep = keep.filter(function (k) {
      if (room && used + k[1].size > room) {
        data.append("vynechano", k[1].name + "|" + whole);
        return false;
      }
      used += k[1].size;
      return true;
    });
    if (had && !keep.length) { return null; }
    keep.forEach(function (k) { data.append(k[0], k[1]); });
    return data;
  }

  // Files can be dropped on a file field of such a form (<form data-pretahni>): on its whole label, not only
  // on the small button of the browser.
  Array.prototype.forEach.call(document.querySelectorAll("form[data-pretahni] label, label.ob-drop"), function (label) {
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

  // Search folds case and accents the same way on both sides (only for comparing; what is shown stays as it is):
  // "pribram" finds "Příbram", "BELO" finds "Bělo". Every word of the query has to be in the row.
  function fold(text) {
    return String(text || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLocaleLowerCase("cs");
  }
  window.obFold = fold;

  // Filters of a table, all of them at once: <input type="search" data-filter="#table-id"> looks for words in the
  // row (or in its data-hledat), <select data-filter="#table-id" data-filter-attr="sport"> keeps the rows whose
  // data-sport is the chosen value. <p data-filter-empty="#table-id" hidden> is shown when no row is left.
  var filtered = {};
  Array.prototype.forEach.call(document.querySelectorAll("[data-filter]"), function (el) {
    var sel = el.dataset.filter;
    (filtered[sel] = filtered[sel] || []).push(el);
  });
  Object.keys(filtered).forEach(function (sel) {
    var table = document.querySelector(sel), controls = filtered[sel];
    if (!table || !table.tBodies.length) { return; }
    var empty = document.querySelector('[data-filter-empty="' + sel + '"]');
    var rows = Array.prototype.slice.call(table.tBodies[0].rows);
    rows.forEach(function (r) { r.dataset.obFold = fold(r.dataset.hledat || r.textContent); });
    function apply() {
      var shown = 0;
      rows.forEach(function (r) {
        var ok = controls.every(function (c) {
          var v = c.value.trim();
          if (!v) { return true; }
          if (c.tagName === "SELECT") { return (" " + (r.getAttribute("data-" + c.dataset.filterAttr) || "") + " ").indexOf(" " + v + " ") >= 0; }
          return fold(v).split(/\s+/).every(function (w) { return r.dataset.obFold.indexOf(w) >= 0; });
        });
        r.hidden = !ok;
        if (ok) { shown += 1; }
      });
      if (empty) { empty.hidden = shown > 0; }
      var count = document.querySelector('[data-filter-count="' + sel + '"]');
      if (count) { count.textContent = t("Zobrazeno %(n)s z %(of)s", { n: shown, of: rows.length }); }
    }
    controls.forEach(function (c) { c.addEventListener(c.tagName === "SELECT" ? "change" : "input", apply); });
    var reset = document.querySelector('[data-filter-reset="' + sel + '"]');
    if (reset) {
      reset.addEventListener("click", function (ev) {
        if (reset.tagName === "A" && reset.getAttribute("href") !== "#") { return; }  // the link also clears the filters of the server
        ev.preventDefault();
        controls.forEach(function (c) { c.value = ""; });
        apply();
      });
    }
    apply();
  });

  // Order of the rows chosen in a list: <select data-razeni="#table-id"> with options "key:asc|desc"; the rows carry
  // data-k-key (a number or a text). Clicking a column heading still sorts as well (th[data-sort] above).
  Array.prototype.forEach.call(document.querySelectorAll("select[data-razeni]"), function (select) {
    var table = document.querySelector(select.dataset.razeni);
    if (!table || !table.tBodies.length) { return; }
    function order() {
      var parts = select.value.split(":"), key = "k" + parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
      var dir = parts[1] === "asc" ? 1 : -1, body = table.tBodies[0];
      var rows = Array.prototype.slice.call(body.rows);
      rows.sort(function (a, b) {
        var x = a.dataset[key] || "", y = b.dataset[key] || "", number = /^-?\d+(\.\d+)?$/;
        if (x === "" || y === "") { return x === y ? 0 : x === "" ? 1 : -1; }  // without a value always last
        if (number.test(x) && number.test(y)) { return (parseFloat(x) - parseFloat(y)) * dir; }
        return x.localeCompare(y, "cs") * dir;
      });
      rows.forEach(function (r) { body.appendChild(r); });
      Array.prototype.forEach.call(table.querySelectorAll("th[aria-sort]"), function (th) { th.removeAttribute("aria-sort"); });
    }
    select.addEventListener("change", order);
    if (select.value !== select.options[0].value) { order(); }
  });

  // What was chosen in a file field: the name, the size and a preview of a picture, with a way to take it back.
  // A file the field or the server would not take is marked at once (the same limits upload() applies below).
  function size(bytes) {
    return bytes >= 1048576 ? (bytes / 1048576).toFixed(1).replace(".", OBAPP_LANG === "en" ? "." : ",") + " MB"
      : Math.max(1, Math.round(bytes / 1024)) + " kB";
  }
  var OBAPP_LANG = (window.OBAPP && window.OBAPP.lang) || "cs";
  Array.prototype.forEach.call(document.querySelectorAll("form[data-nahravani] input[type=file], input[type=file][data-vyber]"), function (input) {
    var list = document.createElement("ul");
    list.className = "vybrane-soubory";
    list.setAttribute("aria-live", "polite");
    list.hidden = true;
    (input.closest("label") || input).insertAdjacentElement("afterend", list);
    var urls = [];
    function show() {
      urls.forEach(function (u) { URL.revokeObjectURL(u); });
      urls = [];
      list.textContent = "";
      var files = Array.prototype.slice.call(input.files || []);
      list.hidden = !files.length;
      var max = parseInt(input.getAttribute("data-max") || "0", 10), whole = (window.OBAPP && window.OBAPP.maxUpload) || 0;
      var ok = (input.accept || "").split(",").map(function (x) { return x.trim().toLowerCase(); }).filter(Boolean);
      files.forEach(function (f, i) {
        var li = document.createElement("li"), name = document.createElement("span"), sz = document.createElement("span");
        name.className = "jmeno";
        name.textContent = f.name;
        sz.className = "velikost";
        sz.textContent = size(f.size);
        li.append(name, sz);
        var why = "";
        if (ok.length && !ok.some(function (ext) { return f.name.toLowerCase().slice(-ext.length) === ext; })) {
          why = t("tenhle druh souboru pole nepřijme");
        } else if ((max && f.size > max) || (whole && f.size > whole)) {
          why = t("je větší, než server přijme; nenahraje se");
        }
        if (why) {
          var no = document.createElement("span");
          no.className = "odmitnuto";
          no.textContent = why;
          li.appendChild(no);
        } else if (/^image\/(png|jpeg)$/.test(f.type) && f.size < 40 * 1048576) {
          var img = document.createElement("img"), u = URL.createObjectURL(f);
          urls.push(u);
          img.src = u;
          img.alt = t("Náhled: %(name)s", { name: f.name });
          li.insertBefore(img, name);
        }
        var drop = document.createElement("button");
        drop.type = "button";
        drop.className = "btn btn-maly btn-tichy";
        drop.textContent = t("Odebrat");
        drop.setAttribute("aria-label", t("Odebrat %(name)s", { name: f.name }));
        drop.addEventListener("click", function () {
          try {
            var dt = new DataTransfer();
            Array.prototype.forEach.call(input.files, function (g, k) { if (k !== i) { dt.items.add(g); } });
            input.files = dt.files;
          } catch (e) { input.value = ""; }
          show();
          input.dispatchEvent(new Event("ob-vyber", { bubbles: true }));
          input.focus();
        });
        li.appendChild(drop);
        list.appendChild(li);
      });
    }
    input.addEventListener("change", show);
    input.form && input.form.addEventListener("reset", function () { setTimeout(show, 0); });
  });

  // Choices that look like buttons (aria-pressed), each with its own part of the page: <div data-volby="key">
  // <button class="volba" data-volba="a" aria-pressed="false"> … and <div data-volba-panel="a" hidden>. Choosing
  // shows only that part; nothing that is stored changes. Files chosen in the part being left are not sent
  // unseen: the reader is asked whether to drop them or to stay.
  Array.prototype.forEach.call(document.querySelectorAll("[data-volby]"), function (box) {
    var buttons = box.querySelectorAll("[data-volba]"), key = "ob-volba-" + box.dataset.volby;
    var panels = document.querySelectorAll("[data-volba-panel]"), prompt = document.querySelector("[data-volba-vyzva]");
    function chosenFiles(panel) {
      return Array.prototype.some.call(panel.querySelectorAll("input[type=file]"), function (f) { return f.files && f.files.length; });
    }
    function pick(name, quiet) {
      var leaving = Array.prototype.filter.call(panels, function (p) { return !p.hidden && p.dataset.volbaPanel !== name; });
      if (!quiet && leaving.some(chosenFiles)) {
        if (!window.confirm(t("V původní variantě máš vybrané soubory, které se ještě nenahrály. Zrušit jejich výběr a přepnout?"))) { return; }
        leaving.forEach(function (p) {
          Array.prototype.forEach.call(p.querySelectorAll("input[type=file]"), function (f) { f.value = ""; f.dispatchEvent(new Event("change")); });
        });
      }
      Array.prototype.forEach.call(buttons, function (b) { b.setAttribute("aria-pressed", b.dataset.volba === name ? "true" : "false"); });
      Array.prototype.forEach.call(panels, function (p) { p.hidden = p.dataset.volbaPanel !== name; });
      if (prompt) { prompt.hidden = !!name; }
      try { if (name) { sessionStorage.setItem(key, name); } } catch (e) { /* no storage: only for this page */ }
    }
    Array.prototype.forEach.call(buttons, function (b) {
      b.addEventListener("click", function () { pick(b.dataset.volba); });
    });
    var start = box.dataset.vychozi || "";
    try { start = sessionStorage.getItem(key) || start; } catch (e) { /* no storage */ }
    if (start && box.querySelector('[data-volba="' + start + '"]')) { pick(start, true); }
    // a link elsewhere on the page can open a variant: <a data-otevri-volbu="b" href="#podklady">
    Array.prototype.forEach.call(document.querySelectorAll("[data-otevri-volbu]"), function (a) {
      a.addEventListener("click", function () { pick(a.dataset.otevriVolbu); });
    });
  });

  // A risky step asks first (deleting, disconnecting, a change for the whole race): <form data-potvrdit="text">
  // or <button data-potvrdit="text">. Ordinary steps that are easy to take back ask nothing.
  document.addEventListener("submit", function (ev) {
    var form = ev.target, text = form.getAttribute && form.getAttribute("data-potvrdit");
    var by = ev.submitter && ev.submitter.getAttribute("data-potvrdit");
    if ((by || text) && !window.confirm(by || text)) { ev.preventDefault(); ev.stopImmediatePropagation(); }
  }, true);
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest ? ev.target.closest("button[data-potvrdit]:not([type=submit])") : null;
    if (b && !window.confirm(b.getAttribute("data-potvrdit"))) { ev.preventDefault(); ev.stopImmediatePropagation(); }
  }, true);

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

  // back to the place kept before the page loaded itself again (keepPlace above)
  (function () {
    var place = null, moved = false;
    try {
      place = JSON.parse(sessionStorage.getItem(PLACE) || "null");
      sessionStorage.removeItem(PLACE);
    } catch (e) { place = null; }
    if (!place || place.path !== here()) { return; }
    var named = location.hash.slice(1);
    if (place.tab && !(named && document.querySelector(".tabpanel#" + CSS.escape(named)))) {
      document.dispatchEvent(new CustomEvent("ob-tab-show", { detail: place.tab }));
    }
    function putBack() {
      if (!place || moved) { return; }
      var el = place.id ? document.getElementById(place.id) : null, r = el && el.getBoundingClientRect();
      if (r && r.height > 0) { window.scrollBy(0, r.top - place.top); } else { window.scrollTo(0, place.y); }
    }
    // the reader's own scrolling wins: no more putting back after it
    ["wheel", "touchstart", "keydown", "mousedown"].forEach(function (name) {
      window.addEventListener(name, function () { moved = true; }, { passive: true, once: true });
    });
    // a notice that came with the new page (the job failed) is at the top, out of sight: the bar says so for a while
    var told = false;
    function tellAbove() {
      var note = document.querySelector("[data-hlaska]"), r = note && note.getBoundingClientRect();
      if (told || !bar || !r || r.bottom > headBottom()) { return; }
      told = true;
      bar.textContent = note.dataset.hlaska + " " + t("Podrobnosti jsou nahoře na stránce.");
      bar.classList.add("ob-prubeh-konec");
      bar.hidden = false;
      bar.addEventListener("click", function () { bar.hidden = true; note.scrollIntoView({ block: "center" }); });
      setTimeout(function () { bar.hidden = true; }, 12000);
    }
    putBack();
    document.addEventListener("ob-vykresleno", function () { putBack(); tellAbove(); });  // the page has its height
    window.addEventListener("load", putBack);
    setTimeout(function () {
      putBack();
      tellAbove();
      place = null;
      try { history.scrollRestoration = "auto"; } catch (e) { /* old browser */ }
    }, 4000);
  })();

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

  // the app on one's own computer: a connected watch with new runs is offered on Přehled závodů and Nahrát běhy.
  // Asked after the page is shown (a slow disk never holds it); nothing is loaded without a click on the watch page.
  var hod = document.querySelector("[data-hodinky]");
  if (hod && window.fetch) {
    var tries = 0;
    var ask = function () {
      fetch(hod.getAttribute("data-hodinky"), { headers: { Accept: "application/json" } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (!d) { return; }
          if (d.pending) { if (++tries < 4) { setTimeout(ask, 4000); } return; }
          if (!d.n) { return; }
          hod.textContent = "";
          var b = document.createElement("b");
          b.textContent = t("Našly se nové aktivity z hodinek (%(n)s).", { n: d.n });
          var a = document.createElement("a");
          a.className = "btn btn-hlavni btn-maly";
          a.href = d.url;
          a.textContent = t("Načíst…");
          var no = document.createElement("button");
          no.type = "button";
          no.className = "btn btn-maly";
          no.textContent = t("Teď ne");
          no.addEventListener("click", function () {
            hod.hidden = true;
            fetch(hod.getAttribute("data-ted-ne"), { method: "POST", headers: { "X-CSRF-Token": window.OBAPP.csrf } });
          });
          hod.append(b, " ", a, " ", no);
          hod.hidden = false;
        })
        .catch(function () { /* no watch, no note */ });
    };
    ask();
  }

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
