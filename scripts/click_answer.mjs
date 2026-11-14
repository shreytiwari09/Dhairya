// Drive headless Chrome over the DevTools protocol: load a page, wait, then scroll in steps and screenshot each.
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, outDir, steps = "10", stepPx = "900", waitMs = "9000", expr = "1"] = process.argv.slice(2);
const port = 9333;
const profile = mkdtempSync(join(tmpdir(), "shots-"));
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  "--window-size=1440,900", "--hide-scrollbars", "--enable-unsafe-swiftshader", "--use-angle=swiftshader",
  "--no-first-run", "about:blank",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function target() {
  for (let i = 0; i < 40; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error("Chrome did not start");
}

const ws = new WebSocket(await target());
await new Promise((r) => (ws.onopen = r));
let id = 0;
const pending = new Map();
ws.onmessage = (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg.result); pending.delete(msg.id); }
};
const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });

await send("Page.enable");
const W = Number(process.env.W || 1440), H = Number(process.env.H || 900), MOBILE = process.env.MOBILE === "1";
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: MOBILE });
await send("Page.navigate", { url });
await sleep(Number(waitMs));
const ev = async (expression) => (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })).result.value;
await ev("document.getElementById('answer').scrollIntoView({block:'center'}); 0");
await sleep(2500);
const rect = JSON.parse(await ev("JSON.stringify(document.getElementById('answer').getBoundingClientRect())"));
const x = rect.x + rect.width / 2, y = rect.y + rect.height / 2;
await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
console.log(await ev("(()=>{const b=document.getElementById('answer');const r=b.getBoundingClientRect();const e=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return 'top element: '+e.tagName+'.'+e.className+'#'+e.id+' | main inert='+document.querySelector('main').inert+' | html='+document.documentElement.className+' | btn disabled='+b.disabled})()"));
const out = [];
for (let i = 0; i < 12; i++) {
  await sleep(1000);
  out.push(await ev("(()=>{const a=document.getElementById('a-caller');return [document.getElementById('who-label').textContent, document.getElementById('status').textContent.slice(0,60), 'paused='+a.paused, 't='+a.currentTime.toFixed(1), 'scrollY='+Math.round(scrollY)].join(' | ')})()"));
}
console.log(out.join("\n"));
ws.close();
chrome.kill();
