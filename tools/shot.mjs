// Screenshots of the web app with headless Chrome over the DevTools protocol (no Playwright needed).
//
//   node tools/shot.mjs SHOTS.json OUT_DIR [--base http://localhost:8000] [--user NAME --pass PASSWORD]
//
// SHOTS.json: [{"name": "01-zavody", "path": "/ob/", "width": 1440, "height": 900, "scale": 1,
//               "theme": "svetly" | "tmavy", "wait": 1500, "eval": "JS run before the shot", "full": true}]
// A walk through the app (tools/shots-foto.json) also uses, in this order:
//   "stay": true                  stay on the page the shot before ended on (after a form was sent)
//   "upload": {"selector": "input[name=course]", "file": "C:/path/photo.jpg"}   put a file into a form field
//   "eval" (as above), "load": true  wait for the page the eval opened (a form sent)
//   "clickAt": "JS returning [[x, y], ...]"   real mouse clicks at those points of the window
//   "until": "JS returning true", "timeout": 300000   wait for it (a job of the worker), checked every second;
//                                 then the page (path) is loaded again
// Needs Node 22+ (built-in WebSocket) and Chrome; set CHROME to its path when it is not in the usual place.
import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i < 0 ? d : args.splice(i, 2)[1]; };
const base = opt("--base", "http://localhost:8000"), user = opt("--user"), pass = opt("--pass");
const port = Number(opt("--port", "9333"));
const [shotsFile, outDir] = args;
if (!shotsFile || !outDir) { console.error("usage: node tools/shot.mjs SHOTS.json OUT_DIR [--base URL] [--user U --pass P]"); process.exit(2); }
const chromePath = process.env.CHROME || ["C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"].find(existsSync);
const profile = mkdtempSync(join(tmpdir(), "ob-shot-"));
const chrome = spawn(chromePath, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  "--hide-scrollbars", "--no-first-run", "--disable-gpu", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" });
      return (await r.json()).webSocketDebuggerUrl;
    } catch { await sleep(250); }
  }
  throw new Error("Chrome did not start");
}

const ws = new WebSocket(await target());
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const waiting = new Map(), events = [];
ws.addEventListener("message", (m) => {
  const d = JSON.parse(m.data);
  if (d.id && waiting.has(d.id)) { waiting.get(d.id)(d); waiting.delete(d.id); } else if (d.method) { events.push(d.method); }
});
const send = (method, params = {}) => new Promise((res, rej) => {
  const n = ++id;
  waiting.set(n, (d) => d.error ? rej(new Error(method + ": " + d.error.message)) : res(d.result));
  ws.send(JSON.stringify({ id: n, method, params }));
});
async function go(url) {
  events.length = 0;
  await send("Page.navigate", { url });
  for (let i = 0; i < 200 && !events.includes("Page.loadEventFired"); i++) { await sleep(50); }
}
const run = (expression) => send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1200, height: 800, deviceScaleFactor: 1, mobile: false });
if (user) {
  await go(base + "/login");
  events.length = 0;
  await run(`document.querySelector("[name=username]").value = ${JSON.stringify(user)};
             document.querySelector("[name=password]").value = ${JSON.stringify(pass)};
             document.querySelector("[name=password]").form.submit();`);
  for (let i = 0; i < 200 && !events.includes("Page.loadEventFired"); i++) { await sleep(50); }
}
mkdirSync(outDir, { recursive: true });
for (const s of JSON.parse(readFileSync(shotsFile, "utf8"))) {
  const width = s.width || 1440, height = s.height || 900;
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: s.scale || 1, mobile: width < 600 });
  // the same picture on every machine: no forced colours (Windows contrast themes), light unless the shot says dark
  await send("Emulation.setEmulatedMedia", { features: [
    { name: "forced-colors", value: "none" },
    { name: "prefers-color-scheme", value: s.theme === "tmavy" ? "dark" : "light" }] });
  if (!s.stay) {
    await go(base + "/login");  // any page of the origin, to set the theme before the real page loads
    await run(s.theme ? `localStorage.setItem("ob-rezim", ${JSON.stringify(s.theme)})` : `localStorage.removeItem("ob-rezim")`);
    await go(base + s.path);
  }
  await sleep(s.wait || 800);
  if (s.upload) {
    const doc = await send("DOM.getDocument", { depth: -1 });
    const node = await send("DOM.querySelector", { nodeId: doc.root.nodeId, selector: s.upload.selector });
    await send("DOM.setFileInputFiles", { nodeId: node.nodeId, files: [s.upload.file] });
  }
  if (s.eval) {
    events.length = 0;
    await run(s.eval);
    if (s.load) { for (let i = 0; i < 1200 && !events.includes("Page.loadEventFired"); i++) { await sleep(50); } }
    await sleep(s.wait || 800);
  }
  if (s.clickAt) {
    for (const [x, y] of (await run(s.clickAt)).result.value || []) {
      for (const type of ["mousePressed", "mouseReleased"]) {
        await send("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: 1 });
      }
      await sleep(600);
    }
  }
  if (s.until) {
    for (let t = 0; t < (s.timeout || 300000); t += 1000) {
      if ((await run(s.until)).result.value === true) { break; }
      await sleep(1000);
    }
    if (s.path) { await go(base + s.path); await sleep(s.wait || 800); }
  }
  if (s.print) { console.log(s.name, "print:", (await run(s.print)).result.value); }
  let clip;
  if (s.full !== false) {
    const m = await send("Page.getLayoutMetrics");
    clip = { x: 0, y: 0, width, height: Math.min(Math.ceil(m.cssContentSize.height), 6000), scale: 1 };
  }
  const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip });
  writeFileSync(join(outDir, s.name + ".png"), Buffer.from(shot.data, "base64"));
  const err = await run(`JSON.stringify((window.__errors || []))`);
  console.log(s.name, err.result.value !== "[]" ? "JS errors: " + err.result.value : "ok");
}
ws.close();
chrome.kill();
await sleep(500);
try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold the folder on Windows */ }
