/* Dhairya. Every number shown comes from data.json; every voice is a real recording. */
(() => {
  // If GSAP fails to load, the page still works: animations are skipped and a plain frame loop drives the replay.
  const gsap = window.gsap || {
    fromTo() {}, from() {}, to() {}, set() {}, registerPlugin() {},
    timeline() { const t = { to: () => t, from: () => t }; return t; },
    ticker: { add(fn) { const loop = () => { fn(); requestAnimationFrame(loop); }; requestAnimationFrame(loop); } },
  };
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const NS = "http://www.w3.org/2000/svg";
  const svgEl = (tag, attrs = {}) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  };
  const query = new URLSearchParams(location.search);
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches || query.has("still");
  const s1 = (v) => `${v.toFixed(1)} s`;
  const s2 = (v) => `${v.toFixed(2)} s`;
  // Round half to even, as the Python report does, so 62.5% reads 62% on every surface.
  const pct = (v) => {
    const x = v * 100;
    const f = Math.floor(x);
    const r = Math.abs(x - f - 0.5) < 1e-9 ? (f % 2 === 0 ? f : f + 1) : Math.round(x);
    return `${r}%`;
  };
  const KIND = { mobile: "Mobile number", otp: "OTP", amount: "Amount", date: "Date" };
  const RIVAL = {
    fixed_500ms: { name: "Ordinary agent", rule: "Ends the turn after 0.5 s of silence" },
    fixed_1500ms: { name: "Patient timer", rule: "Ends the turn after 1.5 s of silence" },
    smart_turn: { name: "Smart Turn†", rule: "Listens to intonation (unfair here: the voices are synthetic)" },
  };
  const ASK = {
    mobile: "a customer is about to read out their mobile number",
    otp: "a customer is about to read out a one-time code",
    amount: "a customer is about to say how much to send",
    date: "a customer is about to say a date",
  };

  const caller = $("#a-caller");
  const agent = $("#a-agent");
  const stage = $("#stage");
  const S = { data: null, lines: {}, call: null, rival: "fixed_500ms", run: null, origin: 0, end: 0, next: "rival", seen: { rival: false, ours: false }, muted: false };

  /* ---------------- the call ---------------- */

  function buildSlots(call) {
    const host = $("#slots");
    host.replaceChildren();
    [...call.truth].filter((c) => c !== "-").forEach((_, i) => {
      if (call.slot === "mobile" && i === 5) host.append(el("span", "slot gap"));
      if (call.slot === "date" && i === 2) host.append(el("span", "slot gap"));
      const slot = el("span", "slot");
      slot.append(el("span", "ch"));
      host.append(slot);
    });
    host.setAttribute("aria-label", "Digits the agent has saved: none yet");
  }

  function setSlots(value, decided, cutIn) {
    const slots = $$("#slots .slot:not(.gap)");
    const chars = value ? [...value].filter((c) => c !== "-") : [];
    slots.forEach((slot, i) => {
      const ch = chars[i] || "";
      const span = $(".ch", slot);
      if (span.textContent !== ch) {
        span.textContent = ch;
        if (ch && !calm) gsap.fromTo(span, { yPercent: 40, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.35, delay: i * 0.03, ease: "expo.out" });
      }
      slot.classList.toggle("has", Boolean(ch));
      slot.classList.toggle("lost", Boolean(decided && cutIn && !ch));
    });
    $("#slots").setAttribute("aria-label", `Digits the agent has saved: ${value || "none yet"}`);
  }

  function buildLine(call) {
    const svg = $("#wave");
    svg.replaceChildren();
    const W = 1000;
    const H = 120;
    const n = call.peaks.length;
    const step = W / n;
    svg.append(svgEl("line", { class: "base", x1: 0, x2: W, y1: H / 2, y2: H / 2 }));
    call.peaks.forEach((p, i) => {
      if (p < 0.02) return;
      const h = Math.max(3, p * H * 0.92);
      svg.append(svgEl("rect", { class: "bar", "data-t": ((i + 0.5) / n) * call.duration_s, x: i * step + step * 0.18, y: (H - h) / 2, width: step * 0.64, height: h, rx: Math.min(2, step * 0.3) }));
    });
    const notes = $("#line-notes");
    notes.replaceChildren();
    call.group_bounds.slice(0, -1).forEach((b, i) => {
      const mid = (b[1] + call.group_bounds[i + 1][0]) / 2;
      const tag = el("span", "pause-tag", `pause ${s1(call.pauses_s[i])}`);
      tag.style.left = `${(100 * mid) / call.duration_s}%`;
      notes.append(tag);
    });
  }

  function buildSaid(call) {
    const host = $("#said");
    host.replaceChildren();
    call.groups.forEach((g, i) => {
      const span = el("span", "", g);
      span.dataset.t = call.group_bounds[i][0];
      host.append(span);
      if (i < call.pauses_s.length) {
        const rest = el("span", "rest", `(${s1(call.pauses_s[i])})`);
        rest.lang = "en";
        rest.dataset.t = call.group_bounds[i][1];
        host.append(rest);
      }
    });
  }

  function setAnswer(kind) {
    const btn = $("#answer");
    const rival = RIVAL[S.rival].name.replace("†", "").toLowerCase();
    const label = { first: "Answer the call", ours: "Same call, with Dhairya", again: "Play both again" }[kind];
    const hint = {
      first: `A recorded call with a synthetic caller, about ${Math.round(S.call.duration_s)} seconds. Sound on.`,
      ours: "The same caller, the same pause.",
      again: `First the ${rival}, then Dhairya.`,
    }[kind];
    btn.dataset.kind = kind === "again" ? "again" : "go";
    $("#answer-label").textContent = label;
    $("#answer-hint").textContent = hint;
    btn.disabled = false;
    S.next = kind === "ours" ? "ours" : "rival";
  }

  function stopRun() {
    caller.pause();
    agent.pause();
    S.run = null;
  }

  function resetStage() {
    $("#agent-says").textContent = "";
    $("#agent-says").className = "agent-says";
    $("#status").textContent = "";
    $("#status").className = "status";
    $$("#line-notes .decide").forEach((n) => n.remove());
    $$("#wave .bar").forEach((b) => b.classList.remove("on", "unheard"));
    for (const span of $("#said").children) span.classList.remove("on");
  }

  function loadCall(call, { scroll = false } = {}) {
    stopRun();
    S.call = call;
    S.seen = { rival: false, ours: false };
    caller.src = call.audio;
    stage.dataset.mode = "idle";
    $("#who-label").textContent = `Press Answer: ${ASK[call.category] || "a customer is about to read out a value"}`;
    $("#who-rule").textContent = "";
    $("#tally").hidden = true;
    buildSlots(call);
    buildLine(call);
    buildSaid(call);
    resetStage();
    setAnswer("first");
    for (const b of $$("#pick button")) b.setAttribute("aria-current", String(b.dataset.id === call.id));
    if (scroll) (window.__scrollTo ? window.__scrollTo("#call") : $("#call").scrollIntoView({ behavior: calm ? "auto" : "smooth" }));
  }

  function start(which, { silent = false } = {}) {
    const call = S.call;
    const key = which === "ours" ? "dhairya" : S.rival;
    const lane = call.lanes[key];
    const clip = which === "ours" ? `readback-${call.id}` : "cutin";
    stopRun();
    resetStage();
    S.run = { which, lane, clip, fired: false };
    stage.dataset.mode = which;
    $("#who-label").textContent = which === "ours" ? "Dhairya is listening" : `${RIVAL[S.rival].name} is listening`;
    $("#who-rule").textContent = which === "ours" ? "Ends the turn when the value is complete" : RIVAL[S.rival].rule;
    setSlots("", false, false);
    $("#answer").disabled = true;
    const clipDur = S.lines[clip] ? S.lines[clip].duration_s : 2;
    S.end = Math.max(call.duration_s, Math.min(lane.decision_t, call.duration_s + 8) + clipDur) + 0.6;
    caller.volume = 1;
    agent.src = `audio/agent/${clip}.wav`; // loaded now, so the agent speaks on time
    agent.load();
    S.muted = silent;
    S.origin = performance.now();
    if (silent) return;
    caller.currentTime = 0;
    const p = caller.play();
    if (p && p.catch) {
      p.catch(() => {
        S.muted = true;
        $("#status").textContent = "The browser blocked sound, so the call plays with captions only.";
        $("#status").className = "status warn";
      });
    }
  }

  function fire(run) {
    const call = S.call;
    const lane = run.lane;
    const cut = lane.cut_in;
    const mark = el("span", `decide ${cut ? "cut" : "open"}`);
    const at = (100 * Math.min(lane.decision_t, call.duration_s)) / call.duration_s;
    mark.style.left = `${at}%`;
    if (at > 86) mark.classList.add("end");
    const tag = el("b");
    tag.append(el("span", "", cut ? "Agent answers" : lane.decision === "nudge" ? "Dhairya asks" : "Dhairya answers"));
    mark.append(tag);
    $("#line-notes").append(mark);
    if (calm) mark.style.opacity = 1;
    else gsap.fromTo(mark, { opacity: 0, scaleY: 0.2 }, { opacity: 1, scaleY: 1, duration: 0.45, ease: "expo.out", transformOrigin: "50% 100%" });

    const says = $("#agent-says");
    says.className = `agent-says ${cut ? "cut" : "open"}`;
    const words = el("span", "", S.lines[run.clip] ? S.lines[run.clip].text : "");
    words.lang = "hi";
    const gloss = el("span", "gloss", cut ? "“Thank you! Noted.”" : `Reads back ${call.truth.replace(/-/g, "–")} and asks “Is that right?”`);
    says.replaceChildren(el("span", "who-tag", cut ? "Agent:" : "Dhairya:"), words, gloss);

    const status = $("#status");
    status.className = "status";
    if (cut) {
      caller.volume = 0.2; // the caller keeps talking under the agent; nobody is listening any more
      status.textContent = `The caller was still speaking. The last ${s1(call.speech_end - lane.decision_t)} of their number was never heard.`;
    } else if (lane.decision === "end_turn" && lane.delay_s != null) {
      status.textContent = `Answered ${s2(lane.delay_s)} after the caller finished, and read the value back.`;
    }
    if (!S.muted && S.lines[run.clip]) {
      agent.currentTime = 0;
      agent.play().catch(() => {});
    }
  }

  function tallyRow(row, name, lane) {
    const fmt = (v) => (v ? v.replace(/-/g, "–") : "nothing");
    row.replaceChildren(el("b", "", name));
    const txt = el("span");
    let lead;
    if (lane.cut_in) lead = "Answered while the caller was still speaking. Saved ";
    else if (lane.decision === "end_turn") lead = `Waited ${s2(lane.delay_s)} after the caller finished. Saved `;
    else lead = "Never had the full value. Saved ";
    txt.append(lead, el("span", "val", fmt(lane.value)), lane.correct ? "." : ", which is incomplete.");
    row.append(txt);
    row.className = `tally-row ${lane.cut_in || !lane.correct ? "cut" : "open"}`;
    row.hidden = false;
  }

  function finish(run) {
    caller.volume = 1;
    S.seen[run.which] = true;
    const call = S.call;
    $("#who-label").textContent = run.which === "ours" ? "Dhairya answered" : `${RIVAL[S.rival].name} answered`;
    if (S.seen.rival) tallyRow($("#tally-rival"), RIVAL[S.rival].name, call.lanes[S.rival]);
    else $("#tally-rival").hidden = true;
    if (S.seen.ours) tallyRow($("#tally-ours"), "Dhairya", call.lanes.dhairya);
    else $("#tally-ours").hidden = true;
    const tally = $("#tally");
    if (tally.hidden) {
      tally.hidden = false;
      if (!calm) gsap.from(tally, { opacity: 0, y: 12, duration: 0.5, ease: "expo.out" });
    }
    if (run.which === "rival") setAnswer("ours");
    else setAnswer(S.seen.rival ? "again" : "first");
    S.run = null;
  }

  function paint(t) {
    const call = S.call;
    const run = S.run;
    const lane = run.lane;
    $("#head").style.left = `${(100 * Math.min(t, call.duration_s)) / call.duration_s}%`;
    for (const span of $("#said").children) span.classList.toggle("on", t >= Number(span.dataset.t));
    const decided = t >= lane.decision_t;
    for (const bar of $$("#wave .bar")) {
      const bt = Number(bar.dataset.t);
      const after = decided && lane.cut_in && bt > lane.decision_t;
      bar.classList.toggle("on", bt <= t && !after);
      bar.classList.toggle("unheard", bt <= t && after);
    }
    let step = null;
    for (const st of lane.steps) if (st.t <= t) step = st;
    setSlots(step ? step.value : "", decided, lane.cut_in);
    if (!decided && run.which === "ours" && step && step.state !== "complete") {
      $("#status").textContent = `Heard ${step.progress}. The line stays open.`;
    }
    if (decided && !run.fired) {
      run.fired = true;
      fire(run);
    }
  }

  function tick() {
    const run = S.run;
    if (!run) return;
    if (!S.muted && !caller.paused && !caller.ended) S.origin = performance.now() - caller.currentTime * 1000;
    const t = (performance.now() - S.origin) / 1000;
    paint(Math.min(t, S.end));
    if (t >= S.end) finish(run);
  }

  /* ---------------- try a pause ---------------- */

  const P = { down: false, t0: 0, raf: 0, cap: 4, timers: [300, 500, 700, 1000, 1500, 2000], truth: "", oursWait: null };

  function buildPause() {
    const call = S.data.calls.find((c) => c.slot === "mobile") || S.data.calls[0];
    P.truth = call.truth;
    P.cap = S.data.meta.hold_cap_s;
    const ours = S.data.results.held_out.rows.find((r) => r.policy === "dhairya");
    P.oursWait = ours ? ours.delay_p50 : null;
    $("#pn-said").textContent = `${call.truth.slice(0, 5)} `;
    $("#pn-rest").textContent = "·····";
    const list = $("#agents");
    list.replaceChildren();
    for (const ms of P.timers) {
      const li = el("li", "agent");
      li.dataset.ms = ms;
      li.append(el("b", "", `${(ms / 1000).toFixed(1)} s timer`), el("span", "", "Cuts in after this much silence"));
      list.append(li);
    }
    const mine = el("li", "agent ours");
    mine.dataset.ours = "1";
    mine.append(el("b", "", "Dhairya"), el("span", "", "Waits for ten digits"));
    list.append(mine);
  }

  function resetPauseRows() {
    for (const li of $$("#agents .agent")) {
      li.classList.remove("cut", "done", "nudge");
      $("span", li).textContent = li.dataset.ours ? "Waiting for ten digits" : "Waiting for silence";
    }
  }

  function pauseFrame() {
    if (!P.down) return;
    const e = (performance.now() - P.t0) / 1000;
    $("#hold-time").textContent = s1(e);
    $("#hold-fill").style.strokeDashoffset = String(339.3 * (1 - Math.min(1, e / (P.cap + 1))));
    for (const li of $$("#agents .agent")) {
      if (li.dataset.ours) {
        if (e >= P.cap && !li.classList.contains("nudge")) {
          li.classList.add("nudge");
          $("span", li).textContent = `At ${P.cap.toFixed(0)} s it says “जी, आगे बोलिए” and keeps listening`;
        }
        continue;
      }
      const ms = Number(li.dataset.ms);
      if (!li.classList.contains("cut") && e * 1000 >= ms) {
        li.classList.add("cut");
        $("span", li).textContent = `Cut in after ${(ms / 1000).toFixed(1)} s of silence. Saved 5 of 10 digits.`;
        if (!calm) gsap.fromTo(li, { x: -6 }, { x: 0, duration: 0.4, ease: "expo.out" });
      }
    }
    if (e > 9) {
      release();
      return;
    }
    P.raf = requestAnimationFrame(pauseFrame);
  }

  function press(ev) {
    if (ev) ev.preventDefault();
    if (P.down) return;
    resetPauseRows();
    P.down = true;
    P.t0 = performance.now();
    $("#hold").classList.add("down");
    $("#hold").setAttribute("aria-pressed", "true");
    $("#hold-label").textContent = "Pausing. Let go to finish";
    $("#pn-rest").classList.remove("on");
    $("#pn-rest").textContent = "·····";
    P.raf = requestAnimationFrame(pauseFrame);
  }

  function release() {
    if (!P.down) return;
    P.down = false;
    cancelAnimationFrame(P.raf);
    $("#hold").classList.remove("down");
    $("#hold").setAttribute("aria-pressed", "false");
    $("#hold-label").textContent = "Hold to pause again";
    const paused = (performance.now() - P.t0) / 1000;
    const cutCount = $$("#agents .agent.cut").length;
    $("#pn-rest").textContent = P.truth.slice(5);
    $("#pn-rest").classList.add("on");
    for (const li of $$("#agents .agent")) {
      if (li.classList.contains("cut")) continue;
      li.classList.add("done");
      $("span", li).textContent = li.dataset.ours
        ? `Got all 10 and answered as soon as the tenth digit arrived${P.oursWait != null ? ` (${s2(P.oursWait)} typical in tests)` : ""}.`
        : `Got all 10, then waited ${(Number(li.dataset.ms) / 1000).toFixed(1)} s of silence before answering.`;
    }
    $("#pause-live").textContent = `You paused ${s1(paused)}. ${cutCount} of ${P.timers.length} timers cut in. Dhairya got all ten digits.`;
  }

  function wirePause() {
    const hold = $("#hold");
    hold.addEventListener("pointerdown", (e) => {
      hold.setPointerCapture(e.pointerId);
      press(e);
    });
    hold.addEventListener("pointerup", release);
    hold.addEventListener("pointercancel", release);
    hold.addEventListener("keydown", (e) => {
      if ((e.key === " " || e.key === "Enter") && !e.repeat) press(e);
    });
    hold.addEventListener("keyup", (e) => {
      if (e.key === " " || e.key === "Enter") release();
    });
    hold.addEventListener("blur", release);
    hold.addEventListener("contextmenu", (e) => e.preventDefault());
  }

  /* ---------------- results ---------------- */

  function buildBig() {
    const rows = S.data.results.held_out.rows;
    const ours = rows.find((r) => r.policy === "dhairya");
    const fast = rows.find((r) => r.policy === "fixed_500ms");
    const set = (id, text) => {
      const n = $(id);
      if (n) n.textContent = text;
    };
    if (fast) set("#big-fast", pct(fast.cut_in_rate));
    if (ours) {
      set("#big-ours", pct(ours.cut_in_rate));
      const wait = $("#big-wait");
      if (wait) {
        wait.textContent = ours.delay_p50.toFixed(2);
        wait.append(el("span", "unit", "s")); // the display face draws a lowercase s as a capital
      }
    }
  }

  function buildLede() {
    const rows = S.data.results.held_out.rows;
    const ours = rows.find((r) => r.policy === "dhairya");
    const fast = rows.find((r) => r.policy === "fixed_500ms");
    const safe = rows.filter((r) => r.policy.startsWith("fixed_") && r.cut_in_rate === 0).sort((a, b) => a.delay_p50 - b.delay_p50)[0];
    const b = (cls, txt) => el("b", cls, txt);
    const parts = [`Tested on ${ours.n} synthetic calls it had never heard. A 0.5 s timer cut off `, b("r", pct(fast.cut_in_rate)), " of callers. "];
    if (safe) parts.push("The quickest timer that cut off nobody made them wait ", b("r", s2(safe.delay_p50)), ". ");
    parts.push("Dhairya cut off ", b("g", pct(ours.cut_in_rate)), ", saved the right value ", b("g", pct(ours.correct_rate)), " of the time, and answered in ", b("g", s2(ours.delay_p50)), ` typically; its slowest answers took ${s2(ours.delay_p95)}.`);
    $("#lede").replaceChildren(...parts);

    const phone = S.data.results.phone8k;
    const po = phone && phone.rows.find((r) => r.policy === "dhairya");
    if (po) {
      const pf = phone.rows.find((r) => r.policy === "fixed_500ms");
      const line = [el("b", "", "On a phone line. "), `The same ${po.n} calls, squeezed to 8 kHz telephone audio (G.711) before Prisma heard them: `];
      if (pf) line.push("the 0.5 s timer cut off ", b("r", pct(pf.cut_in_rate)), "; ");
      line.push("Dhairya cut off ", b("g", pct(po.cut_in_rate)), ", saved the right value ", b("g", pct(po.correct_rate)), " of the time, and answered in ", b("g", s2(po.delay_p50)), ".");
      $("#phone-line").replaceChildren(...line);
      $("#phone-line").hidden = false;
    }
  }

  function buildPlot() {
    const rows = S.data.results.held_out.rows;
    const root = $("#plot");
    for (const n of [...root.children]) if (!["title", "desc"].includes(n.tagName)) n.remove();
    // A narrower drawing on phones, so the chart's text stays readable when scaled down.
    const narrow = matchMedia("(max-width: 600px)").matches;
    const box = narrow ? { l: 52, r: 18, t: 40, b: 70, w: 440, h: 400 } : { l: 74, r: 30, t: 40, b: 70, w: 720, h: 440 };
    root.setAttribute("viewBox", `0 0 ${box.w} ${box.h}`);
    const maxX = 2.5;
    const maxY = 0.8;
    const x = (v) => box.l + ((box.w - box.l - box.r) * v) / maxX;
    const y = (v) => box.h - box.b - ((box.h - box.t - box.b) * v) / maxY;
    for (const v of [0.2, 0.4, 0.6, 0.8]) {
      root.append(svgEl("line", { class: "grid", x1: x(0), x2: x(maxX), y1: y(v), y2: y(v) }));
      const t = svgEl("text", { x: x(0) - 12, y: y(v) + 5, "text-anchor": "end" });
      t.textContent = pct(v);
      root.append(t);
    }
    for (const v of [0, 0.5, 1, 1.5, 2, 2.5]) {
      const t = svgEl("text", { x: x(v), y: y(0) + 30, "text-anchor": "middle" });
      t.textContent = `${v} s`;
      root.append(t);
    }
    root.append(svgEl("line", { class: "axis", x1: x(0), x2: x(maxX), y1: y(0), y2: y(0) }));
    root.append(svgEl("line", { class: "axis", x1: x(0), x2: x(0), y1: y(0), y2: y(maxY) }));
    const xt = svgEl("text", { class: "axis-title", x: x(maxX), y: y(0) + 56, "text-anchor": "end" });
    xt.textContent = narrow ? "Typical wait (timers labelled by silence)" : "Typical wait after the caller finishes";
    const yt = svgEl("text", { class: "axis-title", x: x(0) - 12, y: box.t - 16 });
    yt.textContent = "Callers cut off";
    root.append(xt, yt);

    const timers = rows.filter((r) => r.policy.startsWith("fixed_") && r.delay_p50 != null);
    const curve = svgEl("path", { class: "curve", d: timers.map((r, i) => `${i ? "L" : "M"}${x(r.delay_p50)} ${y(r.cut_in_rate)}`).join(" ") });
    root.append(curve);
    const pts = [];
    for (const r of rows) {
      if (r.delay_p50 == null) continue;
      const px = x(r.delay_p50);
      const py = y(r.cut_in_rate);
      if (r.policy === "dhairya") {
        const halo = svgEl("circle", { class: "halo", cx: px, cy: py, r: 21 });
        const dot = svgEl("circle", { class: "pt-ours", cx: px, cy: py, r: 11 });
        const lab = svgEl("text", { class: "lab-ours", x: px + 34, y: py - 34 });
        lab.textContent = "Dhairya";
        const sub = svgEl("text", { class: "lab-ours-sub", x: px + 34, y: py - 14 });
        sub.textContent = `${pct(r.cut_in_rate)} cut off, ${s2(r.delay_p50)} wait`;
        root.append(halo, dot, lab, sub);
        pts.push(halo, dot);
      } else if (r.policy === "smart_turn") {
        const d = svgEl("rect", { class: "pt-st", x: px - 7, y: py - 7, width: 14, height: 14, transform: `rotate(45 ${px} ${py})` });
        const t = svgEl("text", narrow ? { x: px, y: py + 24, "text-anchor": "middle" } : { x: px - 16, y: py + 5, "text-anchor": "end" });
        t.textContent = "Smart Turn†";
        root.append(d, t);
        pts.push(d);
      } else {
        const c = svgEl("circle", { class: "pt-timer", cx: px, cy: py, r: 7 });
        const low = r.cut_in_rate < 0.05;
        const t = svgEl("text", { x: low ? px + 6 : px + 14, y: low ? py - 15 : py + 5, "text-anchor": "start" });
        t.textContent = `${(Number(r.policy.replace(/\D/g, "")) / 1000).toFixed(1)} s${narrow ? "" : " timer"}`;
        root.append(c, t);
        pts.push(c);
      }
    }
    if (!calm && window.ScrollTrigger) {
      gsap.registerPlugin(ScrollTrigger);
      const len = curve.getTotalLength();
      gsap.set(curve, { strokeDasharray: len, strokeDashoffset: len });
      gsap.timeline({ scrollTrigger: { trigger: root, start: "top 75%", once: true } })
        .to(curve, { strokeDashoffset: 0, duration: 1.1, ease: "power2.inOut", onComplete: () => gsap.set(curve, { clearProps: "strokeDasharray,strokeDashoffset" }) })
        .from(pts, { scale: 0, transformOrigin: "50% 50%", duration: 0.5, ease: "back.out(2)", stagger: 0.06 }, "-=0.6");
    }
  }

  /* ---------------- details ---------------- */

  function buildPick() {
    const host = $("#pick");
    host.replaceChildren();
    const cats = [...new Set(S.data.calls.map((c) => c.category))];
    for (const cat of cats) {
      const col = el("div");
      col.append(el("h3", "", KIND[cat] || cat));
      for (const call of S.data.calls.filter((c) => c.category === cat)) {
        const b = el("button");
        b.type = "button";
        b.dataset.id = call.id;
        b.append(call.truth.replace(/-/g, "–"), el("small", "", `longest pause ${s1(Math.max(0, ...call.pauses_s))}`));
        b.addEventListener("click", () => loadCall(call, { scroll: true }));
        col.append(b);
      }
      host.append(col);
    }
    for (const b of $$(".versus button")) {
      b.addEventListener("click", () => {
        S.rival = b.dataset.rival;
        for (const o of $$(".versus button")) o.setAttribute("aria-pressed", String(o === b));
        loadCall(S.call, { scroll: true });
      });
    }
  }

  function buildFigures() {
    const res = S.data.results.held_out;
    const views = { all: res.rows, ...res.by_category };
    if (S.data.results.phone8k) views.phone8k = S.data.results.phone8k.rows;
    const cats = $("#cats");
    cats.replaceChildren();
    const show = (key) => {
      for (const b of cats.children) b.setAttribute("aria-pressed", String(b.dataset.key === key));
      const body = $("#figures tbody");
      body.replaceChildren();
      for (const r of views[key]) {
        const tr = el("tr", r.policy === "dhairya" ? "ours" : "");
        const cut = el("td", "num", pct(r.cut_in_rate));
        cut.append(el("small", "", `${pct(r.cut_in_ci[0])} to ${pct(r.cut_in_ci[1])}`));
        const right = el("td", "num", pct(r.correct_rate));
        right.append(el("small", "", `${pct(r.correct_ci[0])} to ${pct(r.correct_ci[1])}`));
        tr.append(
          el("td", "", r.policy === "smart_turn" ? "Smart Turn v3.2†" : r.label),
          cut,
          right,
          el("td", "num", r.delay_p50 == null ? "–" : s2(r.delay_p50)),
          el("td", "num", r.delay_p95 == null ? "–" : s2(r.delay_p95)),
        );
        body.append(tr);
      }
      $("#figures-note").textContent = `${views[key][0].n} calls. Small figures are 95% intervals. Typical wait is the median time from the caller's last sound to the answer; slow waits are the 95th percentile. Fixed timers were run live with Prisma's own silence setting. † Smart Turn is disadvantaged by the synthetic voices.`;
    };
    for (const key of Object.keys(views)) {
      const name = key === "all" ? `All ${views.all[0].n}` : key === "phone8k" ? `Phone line, 8 kHz (${views[key][0].n})` : `${KIND[key] || key} (${views[key][0].n})`;
      const b = el("button", "", name);
      b.type = "button";
      b.dataset.key = key;
      b.addEventListener("click", () => show(key));
      cats.append(b);
    }
    show("all");
    const m = S.data.meta;
    $("#cap-s").textContent = m.hold_cap_s.toFixed(0);
    $("#grace-s").textContent = (m.long_grace_ms / 1000).toFixed(1);
    $("#built-test").textContent = `The benchmark: ${m.calls_total} synthetic calls. The first calls of each kind tuned one rule; the other ${m.held_out} were recorded only after the rule was fixed.`;
  }

  /* ---------------- start ---------------- */

  function fail(err) {
    console.error(err); // details for whoever runs the page; visitors get a plain message
    $("#who-label").textContent = "The recorded calls did not load.";
    $("#status").textContent = "Please reload the page. If it keeps happening, the call files are missing from this copy of the site.";
    $("#status").className = "status warn";
    $("#answer").disabled = true;
    $("#lede").textContent = "The measured results did not load. Please reload the page.";
    $("#hold").disabled = true;
    $("#hold-label").textContent = "Unavailable";
    $("#hold-help").textContent = "This demonstration needs the call data, which did not load.";
  }

  $("#answer").disabled = true;
  $("#who-label").textContent = "Loading the recorded call…";
  Promise.all([
    fetch("data.json").then((r) => {
      if (!r.ok) throw new Error(`data.json returned ${r.status}`);
      return r.json();
    }),
    fetch("audio/agent/lines.json").then((r) => (r.ok ? r.json() : {})).catch(() => ({})),
  ])
    .then(([data, lines]) => {
      S.data = data;
      S.lines = lines;
      const wanted = query.get("rival");
      if (wanted && RIVAL[wanted]) {
        S.rival = wanted;
        for (const o of $$(".versus button")) o.setAttribute("aria-pressed", String(o.dataset.rival === wanted));
      }
      $("#answer").addEventListener("click", () => {
        if (!S.run) start(S.next);
      });
      gsap.ticker.add(tick);
      wirePause();
      buildPick();
      loadCall(data.calls[0]);
      buildPause();
      buildLede();
      buildBig();
      buildPlot();
      matchMedia("(max-width: 600px)").addEventListener("change", buildPlot);
      buildFigures();
      if (query.has("played")) {
        // Screenshot aid: the stage as it looks after both runs, without sound.
        for (const which of ["rival", "ours"]) {
          start(which, { silent: true });
          paint(S.end);
          finish(S.run);
        }
      }
    })
    .catch(fail)
    .finally(() => {
      window.__dhairyaReady = true;
      document.dispatchEvent(new Event("dhairya:ready"));
    });
})();
