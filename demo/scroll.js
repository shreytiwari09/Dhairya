/* Dhairya: the cinematic layer. Smooth scroll (Lenis, as on grail-app.com), loader, letter reveals, the hand of cards and the portals.
   Everything here is decoration over a page that already works without it; reduced motion and ?still skip all of it. */
(() => {
  const html = document.documentElement;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches || location.search.includes("still");
  const endLoader = () => {
    if (window.__unblock) window.__unblock();
    else {
      const l = $("#loader");
      if (l) l.remove();
      html.classList.remove("is-loading");
    }
  };

  // The repository link appears only when the builder has set one (data-repo on <body>).
  const repo = document.body.dataset.repo;
  if (repo) {
    const link = $("#repo-link");
    link.href = repo;
    link.hidden = false;
  }

  if (calm || !window.gsap || !window.ScrollTrigger) {
    endLoader();
    return;
  }
  gsap.registerPlugin(ScrollTrigger);
  ScrollTrigger.config({ ignoreMobileResize: true });
  const phone = matchMedia("(max-width: 700px)");
  const fine = matchMedia("(pointer: fine)").matches;

  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  if (!location.hash) scrollTo(0, 0);

  /* ---------- Smooth scroll: Lenis, same lerp as Grail ---------- */
  let lenis = null;
  if (window.Lenis) {
    lenis = new Lenis({ lerp: 0.1, wheelMultiplier: 1, smoothWheel: true });
    lenis.on("scroll", ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000));
    gsap.ticker.lagSmoothing(0);
    lenis.stop(); // until the loader has left
  }
  window.__scrollTo = (target) => {
    const el = typeof target === "string" ? $(target) : target;
    if (!el) return;
    if (lenis) lenis.scrollTo(el, { duration: 1.5, easing: (t) => 1 - Math.pow(1 - t, 4) });
    else el.scrollIntoView({ behavior: "smooth" });
  };
  $$('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const id = a.getAttribute("href");
      if (id.length > 1 && $(id)) {
        e.preventDefault();
        window.__scrollTo(id);
        const t = $(id);
        if (!t.hasAttribute("tabindex")) t.setAttribute("tabindex", "-1");
        t.focus({ preventScroll: true });
      }
    });
  });

  /* ---------- Split headings into letters (full text stays on aria-label) ---------- */
  function split(el) {
    const text = el.textContent.trim().replace(/\s+/g, " ");
    el.setAttribute("aria-label", text);
    el.textContent = "";
    const chars = [];
    text.split(" ").forEach((word, i, all) => {
      const w = document.createElement("span");
      w.className = "w";
      w.setAttribute("aria-hidden", "true");
      [...word].forEach((ch) => {
        const c = document.createElement("span");
        c.className = "c";
        c.textContent = ch;
        w.append(c);
        chars.push(c);
      });
      el.append(w);
      if (i < all.length - 1) el.append(" ");
    });
    return chars;
  }
  const headings = $$(".reveal").map((el) => ({ el, chars: split(el) }));
  headings.forEach((h) => gsap.set(h.chars, { yPercent: 118 }));
  const landing = headings.find((h) => h.el.closest(".landing"));
  const play = (chars) => gsap.to(chars, { yPercent: 0, duration: 1.1, ease: "expo.out", stagger: 0.014 });

  /* ---------- The hands of cards ---------- */
  const heroCards = $$(".landing .gcard");
  gsap.set(heroCards, { y: 460 });

  if (fine && !phone.matches) {
    const mover = heroCards.map((c) => gsap.quickTo(c, "x", { duration: 0.9, ease: "power3" }));
    addEventListener("pointermove", (e) => {
      const m = e.clientX / innerWidth - 0.5;
      mover.forEach((mv, i) => mv(m * (16 + Math.abs(i - 3) * 9) * -1));
    }, { passive: true });
  }

  /* ---------- Intro, after the loader ---------- */
  function intro() {
    const tl = gsap.timeline({ defaults: { ease: "expo.out" } });
    if (landing) tl.to(landing.chars, { yPercent: 0, duration: 1.3, stagger: 0.012 }, 0);
    tl.from(".landing-sub, .built, .cta", { opacity: 0, y: 28, duration: 1, stagger: 0.1 }, 0.5)
      .to(heroCards, { y: 0, duration: 1.5, stagger: 0.08, ease: "power4.out" }, 0.2)
      .from(".bar", { opacity: 0, duration: 0.8, ease: "power1.out" }, 0.7);
  }

  /* ---------- Loader: a card counts to 100 while data and fonts load ---------- */
  const pct = $("#loader-pct");
  const loader = $("#loader");
  const deck = $$(".lcard", loader); // DOM order: the last card is on top
  gsap.set(deck, { rotation: (i) => (i === deck.length - 1 ? 0 : ((i * 47) % 23) - 11) });
  gsap.from(deck, { y: innerHeight * 0.8, duration: 0.9, stagger: 0.05, ease: "power3.out" });
  const count = { v: 0 };
  const show = () => { if (pct) pct.textContent = `${Math.round(count.v)}%`; };
  let minDone = false;
  let ready = Boolean(window.__dhairyaReady);
  let leaving = false;
  function leave() {
    if (leaving || !minDone || !ready) return;
    leaving = true;
    gsap.to(count, {
      v: 100, duration: 0.35, onUpdate: show,
      onComplete: () => {
        // The deck scatters in a spiral, the lilac ground lifts away, and the landing is already moving underneath.
        const R = Math.hypot(innerWidth, innerHeight) * 0.8;
        gsap.timeline()
          .to("#loader-count", { opacity: 0, duration: 0.2 })
          .to([...deck].reverse(), {
            x: (i) => Math.cos(i * 0.78 + 0.5) * R,
            y: (i) => Math.sin(i * 0.78 + 0.5) * R,
            rotation: (i) => (i % 2 ? 1 : -1) * (200 + i * 16),
            scale: 1.4, duration: 1.05, ease: "power2.in", stagger: 0.05,
          }, "<0.05")
          .to(".loader-bg", { yPercent: -100, duration: 0.9, ease: "power3.inOut" }, "<0.35")
          .add(() => intro(), "<0.3")
          .add(() => { endLoader(); if (lenis) lenis.start(); ScrollTrigger.refresh(); }, ">");
      },
    });
  }
  gsap.to(count, { v: 90, duration: 1.5, ease: "power1.out", onUpdate: show, onComplete: () => { minDone = true; leave(); } });
  document.addEventListener("dhairya:ready", () => { ready = true; leave(); });
  setTimeout(() => { ready = true; leave(); }, 6000);

  /* ---------- Scroll choreography (triggers created top to bottom) ---------- */
  // The landing's cards drift down slower than the page, so they seem to hang behind the headline as it leaves.
  gsap.to(".landing .hand", {
    y: 150, ease: "none",
    scrollTrigger: { trigger: ".landing", start: "top top", end: "bottom top", scrub: true },
  });

  // Portals: a card grows until it fills the screen, and becomes the next chapter.
  const bar = $(".bar");
  const portalTriggers = [];
  $$(".portal").forEach((portal) => {
    const card = $(".portal-card", portal);
    const fill = $(".portal-fill", portal);
    const plate = $(".plate", portal);
    const grow = () => Math.max(innerWidth / card.offsetWidth, innerHeight / card.offsetHeight) * 1.08;
    const tl = gsap.timeline({
      defaults: { ease: "none" },
      scrollTrigger: {
        trigger: portal, start: "top top", end: "+=115%", pin: true, scrub: 0.2, invalidateOnRefresh: true,
        onUpdate: (self) => { bar.dataset.on = self.progress < 0.7 ? portal.dataset.from : portal.dataset.to; },
        // The chapter is already in place beneath the portal; taking the portal away reveals it, and its heading rolls in.
        onLeave: () => {
          gsap.set(portal, { autoAlpha: 0 });
          const after = (portal.parentElement.classList.contains("pin-spacer") ? portal.parentElement : portal).nextElementSibling;
          const next = after && headings.find((h) => h.el.closest(".chapter") === after);
          if (next) playOnce(next);
        },
        onEnterBack: () => gsap.set(portal, { autoAlpha: 1 }),
      },
    })
      .fromTo(card, { scale: 0.78, rotation: -7, y: 90 }, { scale: 1, rotation: 0, y: 0, duration: 0.22, ease: "power2.out" })
      .to(card, { scale: grow, duration: 0.6, ease: "power2.in" })
      .set(plate, { autoAlpha: 0 }, ">-0.02") // the card has outgrown the label by now; never show it half-faded
      .set(fill, { opacity: 1 }, "<"); // the card now covers the screen, so the swap to the next ground is a clean cut
    portalTriggers.push(tl.scrollTrigger);
  });

  // Letter reveals for every heading after the landing.
  const afterPortal = (el) => {
    const prev = el.closest(".chapter").previousElementSibling;
    return Boolean(prev && (prev.classList.contains("portal") || prev.classList.contains("pin-spacer")));
  };
  const played = new Set();
  const playOnce = (h) => { if (!played.has(h)) { played.add(h); play(h.chars); } };
  headings.filter((h) => h !== landing).forEach((h) => {
    ScrollTrigger.create({ trigger: h.el, start: "top 88%", once: true, onEnter: () => {
      // A heading just after a portal waits for the portal to leave; a late fallback catches anyone who lands past it.
      if (afterPortal(h.el)) return;
      playOnce(h);
    } });
    if (afterPortal(h.el)) {
      ScrollTrigger.create({ trigger: h.el, start: "top 40%", once: true, onEnter: () => playOnce(h) });
    }
  });

  // The top bar steps out of the way while reading downwards and returns on any upward scroll.
  ScrollTrigger.create({
    start: 0, end: "max",
    onUpdate: (self) => {
      bar.classList.toggle("solid", self.scroll() > 80);
      const hide = self.direction === 1 && self.scroll() > 240;
      gsap.to(bar, { yPercent: hide ? -110 : 0, duration: 0.4, ease: "power2.out", overwrite: true });
    },
  });
  // ...and takes the ink colour of the chapter beneath it; it returns on keyboard focus.
  $$(".chapter").forEach((ch) => {
    ScrollTrigger.create({ trigger: ch, start: "top 48px", end: "bottom 48px", onToggle: (self) => { if (self.isActive) bar.dataset.on = ch.dataset.ground; } });
  });
  bar.addEventListener("focusin", () => gsap.to(bar, { yPercent: 0, duration: 0.3, overwrite: true }));

  /* ---------- Settle on a whole page ----------
     After scrolling stops inside a short stretch (landing, problem, why, each portal, the ending) the page glides on to the nearest resting
     point in the direction of travel, so a light scroll never leaves a chapter half in view. Long chapters scroll freely. */
  if (lenis) {
    const top = (el) => el.getBoundingClientRect().top + lenis.scroll;
    const points = () => {
      const pts = ["#top", "#problem", "#why", "#end"].map((s) => top($(s)));
      portalTriggers.forEach((st) => {
        const len = st.end - st.start;
        // start: card arriving; +0.27: card at full size; end + 1: card has filled the screen and the chapter is in place.
        pts.push(st.start, st.start + len * 0.27, st.end + 1);
      });
      pts.push(ScrollTrigger.maxScroll(window));
      return pts.sort((a, b) => a - b);
    };
    let timer = 0;
    let last = 0;
    let dir = 1;
    let rest = 0; // where the page last came to rest
    lenis.on("scroll", ({ scroll }) => {
      if (Math.abs(scroll - last) > 0.5) dir = scroll > last ? 1 : -1;
      last = scroll;
      clearTimeout(timer);
      timer = setTimeout(function settle() {
        if (lenis.isScrolling && Math.abs(lenis.velocity) > 0.05) { timer = setTimeout(settle, 120); return; }
        const y = lenis.scroll;
        const prev = rest;
        rest = y;
        // Arriving from above and stopping just inside a long chapter: go to its start so its heading and first content are whole.
        const entries = [...portalTriggers.map((st) => st.end + 1), top($("#details"))];
        if (dir === 1) {
          for (const e of entries) {
            if (prev < e - 4 && y > e + 3 && y - e < innerHeight * 0.45) {
              rest = e;
              lenis.scrollTo(e, { duration: 0.8, easing: (t) => 1 - Math.pow(1 - t, 4) });
              return;
            }
          }
        }
        const pts = points();
        let lo = pts[0];
        let hi = pts[pts.length - 1];
        for (const p of pts) { if (p <= y + 0.5) lo = p; }
        for (const p of pts) { if (p > y + 0.5) { hi = p; break; } }
        if (hi - lo > innerHeight * 1.3 || hi - lo < 4) return; // inside a long chapter: leave it alone
        if (y - lo < 3 || hi - y < 3) return; // already there
        const toward = dir === 1 ? (y - lo > (hi - lo) * 0.08 ? hi : lo) : hi - y > (hi - lo) * 0.08 ? lo : hi;
        rest = toward;
        lenis.scrollTo(toward, { duration: 0.85, easing: (t) => 1 - Math.pow(1 - t, 4) });
      }, 170);
    });
  }

  /* ---------- Keep trigger positions honest as the page changes height ---------- */
  document.fonts.ready.then(() => ScrollTrigger.refresh());
  document.addEventListener("dhairya:ready", () => setTimeout(() => ScrollTrigger.refresh(), 250));
  $$("details").forEach((d) => d.addEventListener("toggle", () => ScrollTrigger.refresh()));
  phone.addEventListener("change", () => ScrollTrigger.refresh());
})();
