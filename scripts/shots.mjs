// Drive headless Chrome over the DevTools protocol: load a page, wait, then scroll in steps and screenshot each.
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const [url, outDir, steps = "10", stepPx = "900", waitMs = "9000"] = process.argv.slice(2);
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
for (let i = 0; i <= Number(steps); i++) {
  const shot = await send("Page.captureScreenshot", { format: "jpeg", quality: 70 });
  writeFileSync(join(outDir, `s${String(i).padStart(2, "0")}.jpg`), Buffer.from(shot.data, "base64"));
  // Real wheel events, so scroll-driven libraries react as they would for a person.
  for (let k = 0; k < 6; k++) {
    await send("Input.dispatchMouseEvent", { type: "mouseWheel", x: W / 2, y: H / 2, deltaX: 0, deltaY: Number(stepPx) / 6 });
    await sleep(120);
  }
  await sleep(Number(process.env.SETTLE || 1400));
}
const info = await send("Runtime.evaluate", { expression: "JSON.stringify({h: document.documentElement.scrollHeight, y: scrollY, title: document.title})", returnByValue: true });
console.log(info.result.value);
ws.close();
chrome.kill();
