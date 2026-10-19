/* =========================================================
   STIZO NPC – interacțiuni (vanilla JS, fără dependențe)
   Fiecare modul verifică dacă elementul există, ca același
   fișier să poată fi inclus și pe paginile legale / 404.
   ========================================================= */
(() => {
  'use strict';

  const root = document.documentElement;
  // Marcăm că JS rulează: abia acum ascundem elementele .reveal (fără JS rămân vizibile)
  root.classList.add('js');

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

  /* ---------- Anul curent în footer ---------- */
  const year = $('#year');
  if (year) year.textContent = String(new Date().getFullYear());

  /* ---------- Header: fundal blur după primii pixeli de scroll ---------- */
  const header = $('#site-header');
  const timeline = $('#timeline');
  let ticking = false;

  const onScroll = () => {
    if (header) header.classList.toggle('is-scrolled', window.scrollY > 16);

    // Linia timeline-ului se umple proporțional cu cât din el a trecut de mijlocul ecranului
    if (timeline) {
      const r = timeline.getBoundingClientRect();
      const p = clamp((window.innerHeight * 0.6 - r.top) / r.height, 0, 1);
      timeline.style.setProperty('--progress', p.toFixed(3));
    }
    ticking = false;
  };
  // requestAnimationFrame = maxim un calcul pe cadru, scroll fluid (bun pentru INP)
  window.addEventListener('scroll', () => {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  /* ---------- Meniu mobil ---------- */
  const burger = $('#burger');
  const menu = $('#nav-menu');
  if (burger && menu) {
    const setMenu = (open) => {
      burger.setAttribute('aria-expanded', String(open));
      burger.setAttribute('aria-label', open ? 'Închide meniul' : 'Deschide meniul');
      menu.classList.toggle('is-open', open);
    };
    burger.addEventListener('click', () => setMenu(burger.getAttribute('aria-expanded') !== 'true'));
    $$('a', menu).forEach((a) => a.addEventListener('click', () => setMenu(false)));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && menu.classList.contains('is-open')) { setMenu(false); burger.focus(); }
    });
    document.addEventListener('click', (e) => {
      if (menu.classList.contains('is-open') && !menu.contains(e.target) && !burger.contains(e.target)) setMenu(false);
    });
    window.matchMedia('(min-width: 960px)').addEventListener('change', () => setMenu(false));
  }

  /* ---------- Link activ în meniu, după secțiunea vizibilă ---------- */
  const navLinks = $$('.nav-menu ul a[href^="#"]');
  if ('IntersectionObserver' in window && navLinks.length) {
    const byId = new Map(navLinks.map((a) => [a.getAttribute('href').slice(1), a]));
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        navLinks.forEach((a) => a.removeAttribute('aria-current'));
        const link = byId.get(en.target.id);
        if (link) link.setAttribute('aria-current', 'true');
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    byId.forEach((_, id) => { const s = document.getElementById(id); if (s) spy.observe(s); });
  }

  /* ---------- Apariție la derulare (+ contoare) ---------- */
  const animateCount = (el) => {
    const target = Number(el.dataset.count);
    if (reduceMotion) { el.textContent = String(target); return; }
    const t0 = performance.now();
    const dur = 1400;
    const step = (now) => {
      const k = clamp((now - t0) / dur, 0, 1);
      const eased = 1 - Math.pow(1 - k, 3); // ease-out: încetinește spre final
      el.textContent = String(Math.round(target * eased));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  const reveals = $$('.reveal');
  const counters = $$('[data-count]');
  if ('IntersectionObserver' in window) {
    // Mic decalaj între frații din aceeași listă: efect „cascadă”
    reveals.forEach((el) => {
      const idx = [...el.parentElement.children].filter((c) => c.classList.contains('reveal')).indexOf(el);
      if (idx > 0) el.style.transitionDelay = `${Math.min(idx, 4) * 80}ms`;
    });
    const io = new IntersectionObserver((entries, obs) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        en.target.classList.add('is-visible');
        if (en.target.dataset.count) animateCount(en.target);
        obs.unobserve(en.target); // o singură dată, apoi nu mai consumăm resurse
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
    reveals.forEach((el) => io.observe(el));
    counters.forEach((el) => { el.textContent = '0'; io.observe(el); });
  } else {
    reveals.forEach((el) => el.classList.add('is-visible'));
  }

  /* ---------- Filtre portofoliu ---------- */
  const chips = $$('.chip[data-filter]');
  const projects = $$('.project');
  chips.forEach((chip) => chip.addEventListener('click', () => {
    const f = chip.dataset.filter;
    chips.forEach((c) => {
      const on = c === chip;
      c.classList.toggle('is-active', on);
      c.setAttribute('aria-pressed', String(on));
    });
    projects.forEach((p) => {
      const show = f === 'all' || p.dataset.cat.split(' ').includes(f);
      p.hidden = !show;
      p.classList.remove('is-shown');
      if (show) { void p.offsetWidth; p.classList.add('is-shown', 'is-visible'); } // repornește animația
    });
  }));

  /* ---------- Galerie foto (lightbox pe <dialog> nativ) ---------- */
  const lb = $('#lightbox');
  if (lb && typeof lb.showModal === 'function') {
    const img = $('#lb-img', lb);
    const title = $('#lb-title', lb);
    const counter = $('#lb-counter', lb);
    let list = [];
    let idx = 0;
    let name = '';

    const show = (i) => {
      idx = (i + list.length) % list.length;
      img.src = `img/${list[idx]}.webp`;
      img.alt = `${name} – fotografia ${idx + 1} din ${list.length}`;
      counter.textContent = list.length > 1 ? `${idx + 1} / ${list.length}` : '';
      img.style.animation = 'none'; void img.offsetWidth; img.style.animation = '';
      // Preîncărcăm imaginea următoare ca navigarea să fie instantă
      if (list.length > 1) { const n = new Image(); n.src = `img/${list[(idx + 1) % list.length]}.webp`; }
    };

    $$('.project-btn').forEach((btn) => btn.addEventListener('click', () => {
      list = btn.dataset.gallery.split(',');
      name = btn.dataset.title;
      title.textContent = name; // textContent, nu innerHTML – fără risc de injectare
      lb.classList.toggle('is-single', list.length < 2);
      show(0);
      lb.showModal();
      root.style.overflow = 'hidden';
    }));

    lb.addEventListener('close', () => { root.style.overflow = ''; });
    lb.addEventListener('click', (e) => {
      const action = e.target.closest('[data-lb]')?.dataset.lb;
      if (action === 'close') lb.close();
      else if (action === 'prev') show(idx - 1);
      else if (action === 'next') show(idx + 1);
      else if (e.target === lb || e.target.classList.contains('lb-stage')) lb.close(); // clic pe fundal
    });
    lb.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') show(idx - 1);
      if (e.key === 'ArrowRight') show(idx + 1);
    });
    // Glisare pe telefon
    let x0 = null;
    lb.addEventListener('touchstart', (e) => { x0 = e.touches[0].clientX; }, { passive: true });
    lb.addEventListener('touchend', (e) => {
      if (x0 === null || list.length < 2) return;
      const dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1));
      x0 = null;
    });
  }

  /* ---------- Formular de contact ---------- */
  const form = $('#contact-form');
  if (form) {
    const status = $('#form-status');
    const loadedAt = Date.now(); // time-trap: roboții trimit instant
    const setStatus = (msg, type) => { status.textContent = msg; status.className = `form-status ${type}`; };

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      form.classList.add('was-validated');

      if (!form.checkValidity()) {
        setStatus('Te rugăm să completezi câmpurile marcate și să bifezi acordul GDPR.', 'err');
        form.querySelector(':invalid')?.focus();
        return;
      }
      // Honeypot completat sau trimis în sub 3 secunde → robot; răspundem „succes” fără să trimitem
      if (form.botcheck.value || Date.now() - loadedAt < 3000) {
        setStatus('Mulțumim! Mesajul a fost trimis.', 'ok');
        return;
      }
      if (form.access_key.value.startsWith('YOUR_')) {
        setStatus('Formularul nu este încă conectat. Scrie-ne direct la office@stizo-npc.ro sau sună la 0232 230 330.', 'err');
        return;
      }

      const btn = form.querySelector('[type="submit"]');
      btn.disabled = true;
      setStatus('Se trimite…', '');
      try {
        const res = await fetch(form.action, {
          method: 'POST',
          headers: { Accept: 'application/json' },
          body: new FormData(form),
        });
        const data = await res.json();
        if (!res.ok || !data.success) throw new Error(data.message || 'Eroare');
        setStatus('Mulțumim! Am primit cererea și revenim în cel mai scurt timp.', 'ok');
        form.reset();
        form.classList.remove('was-validated');
      } catch {
        setStatus('Nu am putut trimite mesajul. Te rugăm să ne scrii la office@stizo-npc.ro.', 'err');
      } finally {
        btn.disabled = false;
      }
    });
  }

  /* ---------- Consimțământ cookie granular ---------- */
  const banner = $('#cookie');
  const fab = $('.cookie-fab');
  if (banner) {
    const KEY = 'stizo-consent-v1';
    const cform = $('#cookie-form', banner);
    const read = () => { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } };

    // Aici se încarcă scripturile terțe, DOAR pe categoria acceptată.
    // Momentan site-ul nu folosește analitice/marketing, deci nu se încarcă nimic.
    const apply = (c) => {
      if (c.analytics) { /* ex.: încărcare Google Analytics / Plausible */ }
      if (c.marketing) { /* ex.: pixel Meta */ }
    };
    const save = (analytics, marketing) => {
      const c = { analytics, marketing, date: new Date().toISOString() };
      try { localStorage.setItem(KEY, JSON.stringify(c)); } catch { /* mod privat: ignorăm */ }
      apply(c);
      banner.hidden = true;
      if (fab) fab.hidden = false;
    };
    const open = () => {
      const c = read();
      cform.analytics.checked = !!c?.analytics;
      cform.marketing.checked = !!c?.marketing;
      banner.hidden = false;
      if (fab) fab.hidden = true;
      // Deschis manual = vrea să modifice, deci arătăm direct categoriile
      $('.cookie-more', banner).open = true;
      cform.querySelector('input[name="analytics"]').focus();
    };

    const existing = read();
    if (existing) { apply(existing); if (fab) fab.hidden = false; }
    else banner.hidden = false;

    cform.addEventListener('submit', (e) => { e.preventDefault(); save(cform.analytics.checked, cform.marketing.checked); });
    $('[data-consent="all"]', banner).addEventListener('click', () => save(true, true));
    $('[data-consent="reject"]', banner).addEventListener('click', () => save(false, false));
    $$('[data-open-cookies]').forEach((b) => b.addEventListener('click', open));
  }
})();
