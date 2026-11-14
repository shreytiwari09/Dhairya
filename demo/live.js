/* Dhairya, live mode. The visitor speaks into the microphone; the browser streams 16 kHz PCM to the live server over a
   WebSocket, and the server runs the same turn-taking code that produced the results. Everything shown comes from the
   server's messages. If the server is absent the block says so and the recorded calls work as always. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const root = $("live");
  if (!root) return;

  // ---------- Settings ----------
  const FAKE = new URLSearchParams(location.search).has("livefake"); // test mode: no microphone, silence frames. Harmless in production.
  const CAP_S = 45; // hard limit per turn, as agreed with the server
  const CHUNK = 960; // 60 ms at 16 kHz
  const STATUS_TIMEOUT_MS = 25000; // a sleeping host takes about 30 s to wake; the status call is also the warm-up
  const CONNECT_TIMEOUT_MS = 20000;
  const RESULT_GRACE_MS = 20000; // after we send "stop", how long we wait for the result

  const SLOTS = {
    mobile: { len: 10, group: 5, hint: "Read ten digits, in Hindi or English, with a pause in the middle." },
    otp6: { len: 6, hint: "Read six digits, for example 4 8 2 9 1 7, and pause after the third." },
    otp4: { len: 4, hint: "Read four digits, for example 4 8 2 9, and pause after the second." },
    amount: { hint: "Say an amount, for example “twelve thousand five hundred rupees”, and pause after “twelve thousand”." },
    date: { hint: "Say a date, for example “fifteen March”, and pause between the day and the month." },
  };
  const PHASES = {
    idle: "Not started",
    connecting: "Connecting",
    agent: "The agent is speaking",
    listening: "Listening",
    decided: "Dhairya answered after the last word",
    done: "Call finished",
  };
  const MSG = {
    loading: "Waking the live agent…",
    busy: "Someone else is talking to it. Try again in a minute.",
    paused: "Live mode is paused for today. The recorded calls above work as always.",
    offline: "Live mode is offline right now. The recorded calls above are real recordings of the same system.",
    blocked: "The microphone is blocked. Allow it in the browser's address bar, or use the recorded calls above.",
    noMic: "No microphone was found. Connect one, or use the recorded calls above.",
    insecure: "The microphone needs a secure (https) page, and this page does not have one. Use the recorded calls above.",
    micFail: "The microphone could not be started. Check that no other app is using it, or use the recorded calls above.",
    noReach: "Could not reach the live agent. Try again in a moment, or use the recorded calls above.",
    closed: "The connection closed before the call finished. Try again.",
    silent: "Nothing is coming through the microphone. Check that the right one is selected.",
  };

  // ---------- Where the live server is ----------
  function resolveBase() {
    const cfg = String(window.DHAIRYA_LIVE || "").trim().replace(/\/+$/, "");
    if (cfg) return cfg;
    const { protocol, hostname, host, origin } = location;
    if (protocol !== "http:" && protocol !== "https:") return "";
    if (/\.github\.io$/i.test(hostname) || host === "localhost:8765") return "";
    return origin; // served by the live server itself
  }
  const BASE = resolveBase();
  const wsUrl = (slot) => BASE.replace(/^http/, "ws") + "/ws/live?slot=" + encodeURIComponent(slot);

  // ---------- Elements ----------
  const el = {
    banner: $("live-banner"), recheckWrap: $("live-recheck-wrap"), recheck: $("live-recheck"),
    slots: $("lv-slots"), hint: $("lv-hint"), go: $("lv-go"), goLabel: $("lv-go-label"), goHint: $("lv-go-hint"),
    iMic: root.querySelector(".lv-i-mic"), iStop: root.querySelector(".lv-i-stop"),
    meter: $("lv-meter"), status: $("lv-status"), view: $("lv-view"), digits: $("lv-digits"), phase: $("lv-phase"), time: $("lv-time"),
    agentText: $("lv-agent-text"), heard: $("lv-heard"),
    result: $("lv-result"), ours: $("lv-ours"), sub: $("lv-sub"), timers: $("lv-timers"),
  };
  const mk = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const radios = () => [...el.slots.querySelectorAll("input[name=lv-slot]")];
  const selectedSlot = () => (radios().find((r) => r.checked) || { value: "mobile" }).value;
  const s1 = (v) => `${Number(v).toFixed(1)} s`;
  const msLabel = (ms) => `${ms / 1000} s`;
  const fmtVal = (slot, v) => {
    if (v === null || v === undefined || v === "") return null;
    const t = String(v).replace(/\s+/g, "");
    const g = (SLOTS[slot] || {}).group;
    return g && /^\d+$/.test(t) && t.length > g ? t.slice(0, g) + " " + t.slice(g) : String(v);
  };

  // ---------- Block state (from /api/live/status) ----------
  let status = null;
  function setState(state, bannerText) {
    root.dataset.state = state;
    el.banner.textContent = state === "ready" ? "" : bannerText || MSG[state] || "";
    el.banner.hidden = state === "ready";
    el.recheckWrap.hidden = !(state === "busy" || (state === "offline" && !!BASE)); // with no server address there is nothing to check
    syncGo();
  }

  async function checkStatus() {
    setState("loading");
    if (!BASE) { setState("offline"); return; }
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), STATUS_TIMEOUT_MS);
    try {
      const r = await fetch(BASE + "/api/live/status", { signal: ctl.signal, cache: "no-store" });
      if (!r.ok) throw new Error("status " + r.status);
      status = await r.json();
      applyStatus();
    } catch {
      setState("offline");
    } finally {
      clearTimeout(timer);
    }
  }

  function applyStatus() {
    const list = Array.isArray(status.slots) ? status.slots : null;
    // The OTP choice maps to whichever OTP length the server offers; six digits is preferred.
    const otp = radios().find((r) => r.value.startsWith("otp"));
    if (otp && list) otp.value = list.includes("otp6") || !list.includes("otp4") ? "otp6" : "otp4";
    for (const r of radios()) r.disabled = !!list && !list.includes(r.value);
    const firstOk = radios().find((r) => !r.disabled);
    if (firstOk && radios().find((r) => r.checked && r.disabled)) firstOk.checked = true;
    showHint();
    if (!status.enabled || (typeof status.turns_left_today === "number" && status.turns_left_today <= 0)) setState("paused");
    else if (status.busy) setState("busy");
    else setState("ready");
    if (!run) resetView();
  }

  // ---------- Button and view ----------
  let run = null; // the call in progress, or null
  let finished = false; // a call has just ended with a result, so the button says "Try again"

  function syncGo() {
    const state = root.dataset.state;
    const active = !!run;
    el.go.disabled = !active && state !== "ready";
    el.go.dataset.kind = active || finished ? "again" : "";
    el.iMic.hidden = active;
    el.iStop.hidden = !active;
    el.goLabel.textContent = active ? "Stop" : finished ? "Try again" : "Start the live call";
    el.goHint.textContent = active ? "Ends the call early." : FAKE ? "Test mode: no microphone is used." : finished ? "Start a new live call." : "Your browser will ask to use the microphone.";
    for (const r of radios()) if (active) r.disabled = true; else if (status && Array.isArray(status.slots)) r.disabled = !status.slots.includes(r.value); else r.disabled = false;
  }

  function showHint() {
    const s = SLOTS[selectedSlot()];
    el.hint.textContent = s ? s.hint : "";
  }

  function setPhase(p) {
    el.view.dataset.phase = p;
    el.phase.textContent = PHASES[p];
  }

  function setStatus(text, warn) {
    el.status.textContent = text || "";
    el.status.classList.toggle("warn", !!warn);
  }

  // Digit slots: ten for a mobile number (5 + 5), the code length for an OTP, free text for an amount or a date.
  let shownLen = 0;
  function renderDigits(slot, value) {
    const cfg = SLOTS[slot] || {};
    const clean = value ? String(value).replace(/\s+/g, "") : "";
    el.digits.textContent = "";
    el.digits.dataset.kind = cfg.len ? "slots" : "free";
    if (cfg.len) {
      const chars = [...clean];
      const n = Math.max(cfg.len, chars.length);
      for (let i = 0; i < n; i++) {
        if (cfg.group && i === cfg.group) el.digits.append(mk("span", "lv-d gap"));
        const d = mk("span", "lv-d" + (i < chars.length ? " has" : "") + (i >= shownLen && i < chars.length ? " in" : ""), chars[i] || "");
        el.digits.append(d);
      }
      shownLen = chars.length;
    } else {
      el.digits.append(mk("span", "lv-d free" + (clean ? " has" : ""), String(value || "")));
    }
    el.digits.setAttribute("aria-label", clean ? "Heard so far: " + (fmtVal(slot, value) || clean) : "Nothing heard yet");
  }

  function resetView() {
    const slot = run ? run.slot : selectedSlot();
    shownLen = 0;
    renderDigits(slot, "");
    el.heard.textContent = "";
    el.agentText.textContent = "The agent's words appear here.";
    el.agentText.removeAttribute("lang");
    el.agentText.classList.add("empty");
    el.time.textContent = "0.0 s";
    el.result.hidden = true;
    setPhase("idle");
    setStatus("");
    el.meter.classList.remove("on");
    drawMeter(true);
  }

  // ---------- Level meter ----------
  const BARS = 24;
  const levels = new Array(BARS).fill(0);
  for (let i = 0; i < BARS; i++) el.meter.append(mk("i"));
  function drawMeter(reset) {
    if (reset) levels.fill(0);
    const bars = el.meter.children;
    for (let i = 0; i < BARS; i++) bars[i].style.transform = `scaleY(${(0.06 + 0.94 * levels[i]).toFixed(3)})`;
  }
  let lastMeterAt = 0;
  function pushLevel(rms) {
    const lvl = Math.min(1, Math.pow(Math.min(1, rms * 7), 0.7));
    levels.shift();
    levels.push(lvl);
    const now = performance.now();
    if (now - lastMeterAt > 50) { lastMeterAt = now; drawMeter(false); }
    if (run && run.phase === "listening") {
      if (rms > 0.004) run.lastSound = now;
      else if (now - run.lastSound > 5000 && !run.warnedSilent) { run.warnedSilent = true; setStatus(MSG.silent, true); }
      else if (run.warnedSilent && rms > 0.004) { run.warnedSilent = false; setStatus(""); }
    }
  }

  // ---------- Microphone: capture, low-pass, resample to 16 kHz, Int16, 60 ms chunks ----------
  // Self-contained (no outer references) because its source also runs inside the AudioWorklet.
  class Resampler {
    constructor(inRate, onChunk) {
      this.ratio = inRate / 16000;
      this.a = 1 - Math.exp((-2 * Math.PI * 6500) / inRate); // two one-pole low-passes at 6.5 kHz, so little folds back when downsampling
      this.lp = 0;
      this.lp2 = 0;
      this.last = 0;
      this.t = 0;
      this.out = new Int16Array(960);
      this.n = 0;
      this.sq = 0;
      this.onChunk = onChunk;
    }
    push(x) {
      const len = x.length;
      if (!len) return;
      const buf = new Float32Array(len);
      let lp = this.lp;
      let lp2 = this.lp2;
      for (let i = 0; i < len; i++) { lp += this.a * (x[i] - lp); lp2 += this.a * (lp - lp2); buf[i] = lp2; }
      this.lp = lp;
      this.lp2 = lp2;
      let t = this.t;
      while (Math.floor(t) + 1 <= len - 1) {
        const i0 = Math.floor(t);
        const f = t - i0;
        const s0 = i0 < 0 ? this.last : buf[i0];
        let s = s0 + (buf[i0 + 1] - s0) * f;
        s = s > 1 ? 1 : s < -1 ? -1 : s;
        this.sq += s * s;
        this.out[this.n++] = s < 0 ? s * 32768 : s * 32767;
        if (this.n === 960) {
          const pcm = this.out;
          this.onChunk(pcm, Math.sqrt(this.sq / 960));
          this.out = new Int16Array(960);
          this.n = 0;
          this.sq = 0;
        }
        t += this.ratio;
      }
      this.t = t - len;
      this.last = buf[len - 1];
    }
  }

  const WORKLET_SRC = Resampler.toString() + `
    class Tap extends AudioWorkletProcessor {
      constructor() {
        super();
        this.rs = new Resampler(sampleRate, (pcm, rms) => this.port.postMessage({ pcm: pcm.buffer, rms }, [pcm.buffer]));
      }
      process(inputs) {
        const ch = inputs[0] && inputs[0][0];
        if (ch) this.rs.push(ch);
        return true;
      }
    }
    registerProcessor("dhairya-tap", Tap);`;

  // Opens the microphone and calls onChunk(ArrayBuffer, rms) for every 60 ms of 16 kHz mono PCM16.
  async function openMic(ctx, onChunk) {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    const parts = { stream, nodes: [], url: null };
    try {
      const src = ctx.createMediaStreamSource(stream);
      const mute = ctx.createGain(); // some browsers only run a graph that reaches the destination
      mute.gain.value = 0;
      parts.nodes.push(src, mute);
      if (ctx.audioWorklet && window.AudioWorkletNode) {
        parts.url = URL.createObjectURL(new Blob([WORKLET_SRC], { type: "text/javascript" }));
        await ctx.audioWorklet.addModule(parts.url);
        const tap = new AudioWorkletNode(ctx, "dhairya-tap", { numberOfInputs: 1, numberOfOutputs: 1, channelCount: 1 });
        tap.port.onmessage = (e) => onChunk(e.data.pcm, e.data.rms);
        parts.nodes.push(tap);
        src.connect(tap);
        tap.connect(mute);
      } else {
        const rs = new Resampler(ctx.sampleRate, (pcm, rms) => onChunk(pcm.buffer, rms));
        const sp = ctx.createScriptProcessor(4096, 1, 1);
        sp.onaudioprocess = (e) => rs.push(e.inputBuffer.getChannelData(0));
        parts.nodes.push(sp);
        src.connect(sp);
        sp.connect(mute);
      }
      mute.connect(ctx.destination);
    } catch (e) {
      closeMicParts(parts);
      throw e;
    }
    return parts;
  }
  function closeMicParts(parts) {
    if (!parts) return;
    for (const n of parts.nodes) { try { n.disconnect(); } catch { /* already gone */ } }
    for (const t of parts.stream.getTracks()) t.stop();
    if (parts.url) URL.revokeObjectURL(parts.url);
  }

  // ---------- Playing the agent's voice ----------
  // The server gives a short link to the WAV (messages on the socket stay small); a base64 string also works.
  async function wavBytes(m) {
    if (m.audio_url) {
      const r = await fetch(BASE + m.audio_url, { cache: "no-store" });
      if (!r.ok) throw new Error("audio " + r.status);
      return new Uint8Array(await r.arrayBuffer());
    }
    const bin = atob(m.audio);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes;
  }
  function playWav(run0, m) {
    return new Promise((resolve) => {
      wavBytes(m).then((bytes) => play(bytes), () => resolve());
      function play(bytes) {
        const viaElement = () => {
          const url = URL.createObjectURL(new Blob([bytes], { type: "audio/wav" }));
          const a = new Audio(url);
          run0.audio = a;
          const done = () => { URL.revokeObjectURL(url); resolve(); };
          a.onended = done;
          a.onerror = done;
          a.play().catch(done);
        };
        if (run0.ctx && run0.ctx.state !== "closed") {
          run0.ctx.decodeAudioData(bytes.buffer.slice(0)).then((buf) => {
            if (run0.ctx.state === "closed") { resolve(); return; }
            const s = run0.ctx.createBufferSource();
            s.buffer = buf;
            s.connect(run0.ctx.destination);
            s.onended = () => resolve();
            run0.source = s;
            s.start();
          }, viaElement);
        } else viaElement();
      }
    });
  }

  // ---------- The call ----------
  const AC = window.AudioContext || window.webkitAudioContext;

  function cleanup(run0, hard) {
    if (run0.timers) for (const t of run0.timers) { clearTimeout(t); clearInterval(t); }
    run0.timers = [];
    closeMicParts(run0.mic);
    run0.mic = null;
    if (run0.ws) {
      run0.ws.onopen = run0.ws.onmessage = run0.ws.onerror = run0.ws.onclose = null;
      try { if (run0.ws.readyState <= 1) run0.ws.close(); } catch { /* closing anyway */ }
      run0.ws = null;
    }
    const closeCtx = () => { if (run0.ctx && run0.ctx.state !== "closed") run0.ctx.close().catch(() => {}); };
    if (hard || !run0.playing) {
      try { if (run0.source) run0.source.stop(); } catch { /* not started */ }
      if (run0.audio) { try { run0.audio.pause(); } catch { /* ignore */ } }
      closeCtx();
    } else run0.playing.then(closeCtx); // let the agent's last line finish
  }

  // Leave the call and return to the ready state. text: what to say (a plain sentence), warn: show it as a problem.
  function endCall(run0, text, warn, hard) {
    if (run !== run0) return;
    cleanup(run0, hard);
    run = null;
    el.meter.classList.remove("on");
    drawMeter(true);
    if (el.view.dataset.phase !== "done") setPhase(run0.gotResult ? "done" : "idle");
    setStatus(text, warn);
    syncGo();
  }

  async function start() {
    if (run || root.dataset.state !== "ready") return;
    const slot = selectedSlot();
    const my = { slot, phase: "connecting", timers: [], ctx: null, mic: null, ws: null, lastSound: performance.now(), gotResult: false };
    run = my;
    finished = false;
    resetView();
    syncGo();
    setPhase("connecting");
    setStatus("");
    el.meter.classList.add("on");

    if (!FAKE) {
      if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { endCall(my, MSG.insecure, true, true); return; }
      try {
        if (AC) { my.ctx = new AC(); if (my.ctx.state === "suspended") my.ctx.resume().catch(() => {}); } // created inside the click, so the browser lets it play later
        my.mic = await openMic(my.ctx, (buf, rms) => {
          pushLevel(rms);
          const ws = my.ws;
          if (ws && ws.readyState === 1 && !my.stopSent && ws.bufferedAmount < 1e6) ws.send(buf);
        });
      } catch (e) {
        const name = e && e.name;
        const text = name === "NotAllowedError" || name === "SecurityError" ? MSG.blocked
          : name === "NotFoundError" || name === "OverconstrainedError" || name === "DevicesNotFoundError" ? MSG.noMic : MSG.micFail;
        endCall(my, text, true, true);
        return;
      }
      if (run !== my) { cleanup(my, true); return; } // stopped while the browser was asking
    } else {
      // Test mode: 60 ms frames of silence at the same pace as a microphone, and a gentle fake level.
      let k = 0;
      my.fake = setInterval(() => {
        const ws = my.ws;
        const rms = 0.03 + 0.03 * Math.sin(k++ / 5);
        pushLevel(rms);
        if (ws && ws.readyState === 1 && !my.stopSent) ws.send(new ArrayBuffer(CHUNK * 2));
      }, 60);
      my.timers.push(my.fake);
    }

    let ws;
    try { ws = new WebSocket(wsUrl(slot)); } catch { endCall(my, MSG.noReach, true, true); return; }
    ws.binaryType = "arraybuffer";
    my.ws = ws;
    my.timers.push(setTimeout(() => { if (my.ws && my.ws.readyState !== 1) endCall(my, MSG.noReach, true, true); }, CONNECT_TIMEOUT_MS));
    ws.onopen = () => setStatus("");
    ws.onerror = () => {};
    ws.onclose = () => {
      if (my.gotResult) return;
      if (my.userStopped) endCall(my, "Stopped.", false, true);
      else endCall(my, my.opened ? MSG.closed : MSG.noReach, true, true);
    };
    ws.onmessage = (e) => {
      if (typeof e.data !== "string") return;
      let m;
      try { m = JSON.parse(e.data); } catch { return; }
      my.opened = true;
      handle(my, m);
    };
  }

  function sendStop(my) {
    if (my.stopSent) return;
    my.stopSent = true;
    try { if (my.ws && my.ws.readyState === 1) my.ws.send(JSON.stringify({ type: "stop" })); } catch { /* socket gone */ }
    closeMicParts(my.mic);
    my.mic = null;
    my.timers.push(setTimeout(() => endCall(my, "The live agent did not answer. Try again.", true, true), RESULT_GRACE_MS));
  }

  function stopPressed() {
    const my = run;
    if (!my) return;
    if (!my.ws || my.ws.readyState !== 1 || my.phase === "connecting") { endCall(my, "Stopped.", false, true); return; }
    my.userStopped = true;
    setStatus("Stopping…");
    el.go.disabled = true;
    sendStop(my);
  }

  function startClock(my, offsetS) {
    const t0 = performance.now() - (offsetS || 0) * 1000;
    my.clock = setInterval(() => { if (!my.frozen) el.time.textContent = s1((performance.now() - t0) / 1000); }, 100);
    my.timers.push(my.clock);
  }

  function say(text, my) {
    if (!text) return;
    el.agentText.textContent = text;
    el.agentText.lang = "hi";
    el.agentText.classList.remove("empty");
  }

  function pinHeard() { if (el.heard.scrollTo) el.heard.scrollTo({ top: el.heard.scrollHeight }); }

  function addHeard(m) {
    const li = mk("li", "lv-h " + (m.progress || ""));
    li.append(mk("span", "lv-h-t", s1(m.t || 0)), mk("span", "lv-h-x", m.text || ""));
    li.lastChild.lang = "hi";
    const tag = m.progress === "complete" ? "complete" : m.progress === "open" ? "open" : "";
    if (tag) li.append(mk("span", "lv-h-p", tag));
    el.heard.append(li);
    pinHeard();
  }

  function handle(my, m) {
    if (run !== my) return;
    switch (m.type) {
      case "ready":
        my.phase = "agent";
        if (m.slot && SLOTS[m.slot]) { my.slot = m.slot; renderDigits(m.slot, ""); }
        setPhase("agent");
        say(m.prompt, my);
        break;
      case "agent":
        if (my.phase === "connecting") { my.phase = "agent"; setPhase("agent"); }
        say(m.text, my);
        if (m.audio || m.audio_url) {
          const p = playWav(my, m);
          my.playing = p;
          p.then(() => { if (my.playing === p) my.playing = null; });
        }
        break;
      case "listening":
        my.phase = "listening";
        my.lastSound = performance.now();
        setPhase("listening");
        setStatus("Say it now. Pause wherever you like.");
        startClock(my, 0);
        my.timers.push(setTimeout(() => { setStatus("That is the longest a turn can be, so the call is ending."); sendStop(my); }, CAP_S * 1000));
        break;
      case "heard":
        addHeard(m);
        if (m.value !== null && m.value !== undefined) renderDigits(my.slot, m.value);
        break;
      case "nudge": {
        const li = mk("li", "lv-h nudge");
        li.append(mk("span", "lv-h-t", s1(m.t || 0)), mk("span", "lv-h-x", "The agent asked you to go on."));
        el.heard.append(li);
        pinHeard();
        break;
      }
      case "decided":
        my.phase = "decided";
        my.frozen = true;
        if (typeof m.t === "number") el.time.textContent = s1(m.t);
        closeMicParts(my.mic);
        my.mic = null;
        my.stopSent = true; // no more audio goes out
        if (m.value) renderDigits(my.slot, m.value);
        setPhase("decided");
        setStatus(typeof m.t === "number" ? `Dhairya decided at ${s1(m.t)}. Waiting for the second-pass check.` : "Waiting for the second-pass check.");
        my.timers.push(setTimeout(() => endCall(my, "The live agent did not send its result. Try again.", true, true), RESULT_GRACE_MS));
        el.meter.classList.remove("on");
        drawMeter(true);
        break;
      case "result":
        my.gotResult = true;
        showResult(my, m);
        finished = true;
        setPhase("done");
        endCall(my, `Call finished. Dhairya answered at ${typeof m.decided_t === "number" ? s1(m.decided_t) : "the end"}${m.final_value ? " with " + fmtVal(my.slot, m.final_value) : ""}.`, false, false);
        break;
      case "error": {
        const text = m.message || "Something went wrong. Try again.";
        const code = m.code;
        endCall(my, text, true, true);
        if (code === "limit" || code === "disabled") setState("paused", text);
        else if (code === "busy") setState("busy", text);
        break;
      }
      default:
        break;
    }
  }

  // ---------- The result card ----------
  function showResult(my, r) {
    const slot = r.slot && SLOTS[r.slot] ? r.slot : my.slot;
    const final = fmtVal(slot, r.final_value);
    const dt = typeof r.decided_t === "number" ? s1(r.decided_t) : null;
    el.ours.textContent = "";
    const line = mk("p", "lv-ours-line");
    line.append(mk("b", "", "Dhairya"));
    line.append(mk("span", "", final
      ? ` waited for the whole value and answered${dt ? " at " + dt : ""} with ${final}.`
      : ` did not hear a complete value${dt ? ", and answered at " + dt : ""}.`));
    el.ours.append(line);
    if (r.reply) {
      const q = mk("p", "lv-reply", r.reply);
      q.lang = "hi";
      el.ours.append(q);
    }
    el.ours.classList.toggle("ok", !!final);

    const bits = [];
    const sv = fmtVal(slot, r.streamed_value);
    const pv = fmtVal(slot, r.second_pass_value);
    if (r.agreed === true) bits.push("The second pass through Prisma's REST endpoint agreed with the stream.");
    else if (r.agreed === false) bits.push(`The stream heard ${sv || "nothing"}; the second pass heard ${pv || "nothing"}.`);
    if (r.nudges > 0) bits.push(`The agent asked you to go on ${r.nudges === 1 ? "once" : r.nudges + " times"}.`);
    if (r.extra_digits > 0) bits.push(`You read ${r.extra_digits} extra digit${r.extra_digits === 1 ? "" : "s"}; the agent said so.`);
    if (Array.isArray(r.notes)) for (const n of r.notes) if (typeof n === "string" && n) bits.push(n.endsWith(".") ? n : n + ".");
    el.sub.textContent = bits.join(" ");
    el.sub.hidden = !bits.length;

    el.timers.textContent = "";
    for (const t of Array.isArray(r.timers) ? r.timers : []) {
      const kind = t.cut_in ? "cut" : t.right ? "open" : "none";
      const li = mk("li", "lv-timer " + kind);
      li.append(mk("b", "", `${msLabel(t.ms)} timer`));
      const v = fmtVal(slot, t.value);
      li.append(mk("span", "lv-timer-x", t.ended_t === null || t.ended_t === undefined
        ? "never answered within the call"
        : `answered at ${s1(t.ended_t)} with ${v || "nothing"}`));
      li.append(mk("em", "", t.cut_in ? "Cut in" : t.right ? "Right" : "No answer"));
      el.timers.append(li);
    }
    el.result.hidden = false;
    try {
      const rect = el.result.getBoundingClientRect();
      if (rect.bottom > innerHeight || rect.top < 0) el.result.scrollIntoView({ block: "nearest", behavior: "auto" });
    } catch { /* not worth failing for */ }
  }

  // ---------- Wiring ----------
  el.go.addEventListener("click", () => { if (run) stopPressed(); else start(); });
  el.recheck.addEventListener("click", checkStatus);
  el.slots.addEventListener("change", () => {
    if (run) return;
    finished = false;
    showHint();
    resetView();
    syncGo();
  });
  addEventListener("pagehide", () => { if (run) endCall(run, "", false, true); });

  showHint();
  resetView();
  drawMeter(true);
  syncGo();
  checkStatus();
})();
