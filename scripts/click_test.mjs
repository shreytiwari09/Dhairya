// Drive the real page in headless Chrome: wait for the loader, jump to the call, press Answer twice, hold the pause button,
// and print what the page says at each step. Exits non-zero on any console error.
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const url = process.argv[2] || "http://localhost:8765/";
const port = 9444;
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "click-"))}`,
  "--window-size=1440,900", "--autoplay-policy=no-user-gesture-required", "--enable-unsafe-swiftshader", "--no-first-run", "about:blank",
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl;
for (let i = 0; i < 40 && !wsUrl; i++) {
  try { wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page")?.webSocketDebuggerUrl; } catch {}
  await sleep(250);
}
const ws = new WebSocket(wsUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0;
const waiting = new Map();
const errors = [];
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg.result || msg.error); waiting.delete(msg.id); }
  if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.text + " " + (msg.params.exceptionDetails.exception?.description || ""));
  if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") errors.push("console.error: " + msg.params.args.map((a) => a.value || a.description).join(" "));
};
const send = (method, params = {}) => new Promise((res) => { const i = ++id; waiting.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })).result?.value;

await send("Runtime.enable");
await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url });
await sleep(9000);

const out = {};
out.loaderGone = await ev("!document.getElementById('loader')");
out.motionClass = await ev("document.documentElement.classList.contains('motion')");
out.cards = await ev("document.querySelectorAll('#deck .card').length");
out.dataLoaded = await ev("document.querySelectorAll('#pick button').length");
out.lede = await ev("document.getElementById('lede').textContent.slice(0, 90)");
out.big = await ev("[...document.querySelectorAll('.bigs b')].map(b => b.textContent).join(' | ')");

await ev("document.getElementById('call').scrollIntoView()");
await sleep(1500);
out.answerLabel0 = await ev("document.getElementById('answer-label').textContent");
await ev("document.getElementById('answer').click()");
await sleep(9000);
out.afterRival = await ev("JSON.stringify({mode: document.getElementById('stage').dataset.mode, who: document.getElementById('who-label').textContent, agent: document.getElementById('agent-says').textContent.slice(0, 60), status: document.getElementById('status').textContent.slice(0, 90), next: document.getElementById('answer-label').textContent})");
await ev("document.getElementById('answer').click()");
await sleep(10000);
out.afterOurs = await ev("JSON.stringify({who: document.getElementById('who-label').textContent, agent: document.getElementById('agent-says').textContent.slice(0, 60), digits: [...document.querySelectorAll('#slots .ch')].map(c => c.textContent).join(''), tally: [...document.querySelectorAll('#tally li')].map(l => l.textContent.slice(0, 80)), next: document.getElementById('answer-label').textContent})");

// Hold-to-pause for about 1.2 s
await ev("document.getElementById('pause').scrollIntoView()");
await sleep(800);
await ev("document.getElementById('hold').dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, pointerId: 1}))");
await sleep(1300);
out.holding = await ev("[...document.querySelectorAll('#agents .agent')].map(a => a.className.replace('agent','').trim() + ':' + a.querySelector('b').textContent).join(' | ')");
await ev("document.getElementById('hold').dispatchEvent(new PointerEvent('pointerup', {bubbles: true, pointerId: 1}))");
await sleep(400);
out.released = await ev("document.getElementById('pause-live').textContent");

out.errors = errors;
console.log(JSON.stringify(out, null, 1));
ws.close();
chrome.kill();
process.exit(errors.length ? 1 : 0);
