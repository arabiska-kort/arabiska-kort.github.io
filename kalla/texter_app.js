// Bokens texter. Innehållet (texter.bin och ljud/*.bin) är krypterat och låses upp med
// användarnamn och lösenord. Nyckeln sparas i webbläsaren så att man bara loggar in en gång.
// SALT sätts av bygg_texter.py.
const ITER = 600000;
const NYCKEL_KEY = "texter-nyckel";
const DOLJ_KEY = "texter-dolj";
const app = document.getElementById("app");
let KEY = null, TEXTER = null;
const ljudCache = {};
let player = null, vakt = null, aktiv = null;

const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const tob64 = buf => btoa(String.fromCharCode(...new Uint8Array(buf)));
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
function html(tag, cls, h) { const e = el(tag, cls); e.innerHTML = h; return e; }
function store(fn) { try { return fn(); } catch (e) { return null; } }

// --- Kryptering ---
async function nyckelFran(anv, losen) {
  const bas = await crypto.subtle.importKey("raw", new TextEncoder().encode(anv.trim().toLowerCase() + "\n" + losen),
    "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({ name: "PBKDF2", salt: b64(SALT), iterations: ITER, hash: "SHA-256" },
    bas, { name: "AES-GCM", length: 256 }, true, ["decrypt"]);
}
async function dekryptera(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error("Kunde inte hämta " + url);
  const buf = new Uint8Array(await r.arrayBuffer());
  return crypto.subtle.decrypt({ name: "AES-GCM", iv: buf.slice(0, 12) }, KEY, buf.slice(12));
}
async function laddaTexter() {
  TEXTER = JSON.parse(new TextDecoder().decode(await dekryptera("texter.bin")));
}
function ljudUrl(fil) {
  if (!ljudCache[fil]) {
    ljudCache[fil] = dekryptera(fil).then(b => URL.createObjectURL(new Blob([b], { type: "audio/mpeg" })));
  }
  return ljudCache[fil];
}

// --- Inloggning ---
function visaInloggning(fel) {
  document.title = "Texterna i boken";
  app.innerHTML = "";
  app.append(html("a", "back", "← Ordkorten"));
  app.lastChild.href = "../standardarabiska/";
  const box = el("form", "login");
  box.innerHTML = `
    <p class="ar-title" lang="ar">النصوص</p>
    <h1>Texterna i boken</h1>
    <p class="muted">Logga in för att läsa och lyssna på texterna.</p>
    <label>Användarnamn<input name="anv" autocomplete="username" autocapitalize="none" spellcheck="false" required></label>
    <label>Lösenord<input name="losen" type="password" autocomplete="current-password" required></label>
    <p class="fel" role="alert">${fel || ""}</p>
    <button type="submit">Logga in</button>`;
  box.addEventListener("submit", async e => {
    e.preventDefault();
    const knapp = box.querySelector("button");
    knapp.disabled = true;
    knapp.textContent = "Loggar in …";
    try {
      KEY = await nyckelFran(box.anv.value, box.losen.value);
      await laddaTexter();
      const raw = await crypto.subtle.exportKey("raw", KEY);
      store(() => localStorage.setItem(NYCKEL_KEY, tob64(raw)));
      visa();
    } catch (err) {
      KEY = null;
      visaInloggning("Fel användarnamn eller lösenord.");
    }
  });
  app.append(box);
  box.anv.focus();
}
function loggaUt() {
  store(() => localStorage.removeItem(NYCKEL_KEY));
  KEY = null; TEXTER = null;
  history.replaceState(null, "", location.pathname);
  visaInloggning();
}

// --- Visning ---
const leb = d => d.dialekt === "leb";
const namn = d => `${leb(d) ? "leb_" : ""}kapitel${d.kapitel}_text${d.text}`;
const DIALEKTER = [
  ["msa", "Standardarabiska", "kapitel 2–6"],
  ["leb", "Libanesiska", "Spoken Lebanese, kapitel 1, 10 och 11"],
];
const LEB_NYCKEL = `Bokens transkription: <code>9</code> ʿayn · <code>'</code> hamza (kort stopp i halsen, ofta där
standardarabiskan har q) · <code>H</code> ح · <code>x</code> خ · <code>G</code> غ · <code>ʃ</code> sh ·
<code>S D T Z</code> de "tunga" ص ض ط ظ · dubbel vokal = lång vokal · dubbel konsonant = shadda ·
<code>*</code> före ett namn. Den arabiska skriften är tillagd och finns inte i boken.`;

function visa() {
  stopp();
  const id = location.hash.slice(1);
  const i = TEXTER.findIndex(d => namn(d) === id);
  if (i < 0) visaLista(); else visaText(i);
  const mal = i < 0 && document.getElementById("dial-" + id);
  if (mal) mal.scrollIntoView(); else window.scrollTo(0, 0);
}

function visaLista() {
  document.title = "Texterna i boken";
  app.innerHTML = "";
  const top = el("div", "toprow");
  const back = el("a", "back", "← Ordkorten");
  back.href = "../standardarabiska/";
  const ut = el("button", "back", "Logga ut");
  ut.addEventListener("click", loggaUt);
  top.append(back, ut);
  app.append(top);
  app.append(html("header", null,
    '<p class="ar-title" lang="ar">النصوص</p><h1>Texterna i boken</h1>' +
    "<p>Texterna och dialogerna i böckerna, med uttal, ord för ord, svenska och bokens inspelningar.</p>"));
  const list = el("div", "list");
  for (const [kod, rubrik, under] of DIALEKTER) {
    const egna = TEXTER.filter(d => (d.dialekt || "msa") === kod);
    if (!egna.length) continue;
    const h = el("h2", "dial", rubrik);
    h.id = "dial-" + kod;
    h.append(el("small", null, under));
    list.append(h);
    let kap = null;
    for (const d of egna) {
      if (d.kapitel !== kap) { kap = d.kapitel; list.append(el("h2", null, "Kapitel " + kap)); }
      list.append(listRad(d));
    }
  }
  app.append(list);
}

function listRad(d) {
  const a = el("a", "item");
  a.href = "#" + namn(d);
  const v = el("div");
  v.append(el("div", "sv-t", d.titel_sv),
    el("div", "meta", `${leb(d) ? "Dialog" : "Text"} ${d.text}${d.ljud ? " · 🔊 ljud" : ""} · ${d.intro}`));
  const ar = el("div", "ar-t", d.titel_ar);
  ar.lang = "ar";
  a.append(v, ar);
  return a;
}

function stopp() {
  if (player) player.pause();
  clearInterval(vakt);
  if (aktiv) aktiv.classList.remove("playing");
  aktiv = null;
}
async function spelaBit(fil, s, e, line) {
  stopp();
  aktiv = line;
  line.classList.add("playing");
  const url = await ljudUrl(fil);
  if (aktiv !== line) return;
  if (!player || player.dataset.fil !== fil) {
    player = new Audio(url);
    player.dataset.fil = fil;
  }
  const start = () => {
    player.currentTime = s;
    player.play().catch(() => {});
    vakt = setInterval(() => { if (player.currentTime >= e || player.ended) stopp(); }, 30);
  };
  if (player.readyState >= 1) start(); else player.addEventListener("loadedmetadata", start, { once: true });
}

function knapparDolj(controls) {
  let dolda = store(() => JSON.parse(localStorage.getItem(DOLJ_KEY))) || [];
  controls.querySelectorAll(".toggle").forEach(btn => {
    const cls = btn.dataset.cls;
    const apply = () => {
      const hidden = dolda.includes(cls);
      document.body.classList.toggle(cls, hidden);
      btn.setAttribute("aria-pressed", String(!hidden));
    };
    apply();
    btn.addEventListener("click", () => {
      dolda = dolda.includes(cls) ? dolda.filter(c => c !== cls) : [...dolda, cls];
      store(() => localStorage.setItem(DOLJ_KEY, JSON.stringify(dolda)));
      apply();
    });
  });
}

function visaText(i) {
  const d = TEXTER[i], prev = TEXTER[i - 1], nxt = TEXTER[i + 1];
  const P = d.personer || [];
  const bok = d.ljud && d.ljud.bok;
  document.title = `${d.titel_sv} – kapitel ${d.kapitel}`;
  app.innerHTML = "";
  const back = el("a", "back", "☰ Alla texter");
  back.href = "#";
  app.append(back);

  const head = el("header");
  const art = el("p", "ar-title", d.titel_ar);
  art.lang = "ar";
  head.append(art, el("h1", null, d.titel_sv), el("p", null,
    `${leb(d) ? "Libanesiska · " : ""}Kapitel ${d.kapitel}, ${leb(d) ? "dialog" : "text"} ${d.text} · ${d.intro}`));
  if (bok) {
    const box = el("div", "audio");
    const wrap = el("div");
    const au = el("audio");
    au.controls = true;
    au.preload = "none";
    wrap.append(el("label", null, "Bokens inspelning"), au);
    box.append(wrap);
    head.append(box);
    const om = d.ljud.omrade;
    ljudUrl(bok).then(u => { au.src = om ? `${u}#t=${om[0]},${om[1]}` : u; }).catch(() => {});
    au.addEventListener("play", () => { if (player && player !== au) stopp(); });
  }
  app.append(head);

  const controls = html("div", "controls",
    '<span>Visa:</span><button class="toggle" data-cls="hide-tr">Uttal</button>' +
    '<button class="toggle" data-cls="hide-lit">Ord för ord</button><button class="toggle" data-cls="hide-sv">Svenska</button>');
  controls.setAttribute("role", "group");
  app.append(controls);
  knapparDolj(controls);

  const dialog = el("div");
  const latin = d.skrift === "latin";  // bokens text är en latinsk transkription
  const fullAr = el("div", latin ? "full-lat" : "full-ar"), fullSv = el("div", "full-sv");
  if (!latin) fullAr.lang = "ar";
  const farg = v => "p" + (P[v].f != null ? P[v].f : v % 3);
  d.delar.forEach((del, k) => {
    const prose = del.vem == null;
    const card = el("article", "turn " + (prose ? "prose" : farg(del.vem)));
    const tag = el("span", "who");
    tag.append(el("span", "num", String(k + 1)), prose ? "Stycke" : P[del.vem].sv);
    card.append(tag);
    del.rader.forEach(([ar, tr, lit, sv], j) => {
      const line = el("div", "line");
      const row = el("div", "ar-row");
      const arEl = el("p", "ar", ar);
      arEl.lang = "ar";
      row.append(arEl);
      const tid = del.tider && del.tider[j];
      if (bok && tid) {
        const b = el("button", "play", "▶");
        b.title = "Lyssna";
        b.addEventListener("click", () => spelaBit(bok, tid[0], tid[1], line));
        row.append(b);
      }
      line.append(row, el("div", "tr", tr));
      if (lit) line.append(el("div", "lit", lit));
      line.append(el("div", "sv", sv));
      card.append(line);
    });
    dialog.append(card);
    const pa = el("p");
    if (!prose) pa.append(el("b", null, (latin ? P[del.vem].bok || P[del.vem].sv : P[del.vem].ar) + ": "));
    pa.append(del.bok);
    fullAr.append(pa);
    const ps = el("p");
    if (!prose) ps.append(el("b", null, P[del.vem].sv + ": "));
    ps.append(del.rader.map(r => r[3]).join(" "));
    fullSv.append(ps);
  });
  app.append(dialog);

  if (d.tips && d.tips.length) {
    const sec = el("section", "extra");
    sec.append(el("h2", null, "Bra att veta"));
    const tips = el("div", "tips");
    for (const t of d.tips) {
      const tip = el("div", "tip");
      tip.append(el("h3", null, t.h));
      if (t.ar) { const a = el("span", "ar-inline", t.ar); a.lang = "ar"; tip.append(a); }
      tip.append(html("p", null, t.p));
      tips.append(tip);
    }
    sec.append(tips);
    app.append(sec);
  }

  const hela = el("section", "extra");
  hela.append(el("h2", null, "Hela texten"));
  for (const [rubrik, inner] of [["Som i boken", fullAr], ["Bara svenska", fullSv], ["Uttalsnyckel", html("p", "key", leb(d) ? LEB_NYCKEL : UTTALSNYCKEL)]]) {
    const det = el("details");
    det.append(el("summary", null, rubrik), inner);
    hela.append(det);
  }
  app.append(hela);

  const fot = el("footer");
  const l = prev ? el("a", "prev", "← " + prev.titel_sv) : el("span", "prev");
  if (prev) l.href = "#" + namn(prev);
  const m = el("a", "alla", "☰ Alla texter");
  m.href = "#";
  const r = nxt ? el("a", "next", nxt.titel_sv + " →") : el("span", "next");
  if (nxt) r.href = "#" + namn(nxt);
  fot.append(l, m, r);
  app.append(fot);
}

window.addEventListener("hashchange", () => { if (TEXTER) visa(); });

// Start: försök med sparad nyckel, annars inloggning.
(async () => {
  const sparad = store(() => localStorage.getItem(NYCKEL_KEY));
  if (sparad) {
    try {
      KEY = await crypto.subtle.importKey("raw", b64(sparad), { name: "AES-GCM" }, true, ["decrypt"]);
      await laddaTexter();
      return visa();
    } catch (e) {
      store(() => localStorage.removeItem(NYCKEL_KEY));
      KEY = null;
    }
  }
  visaInloggning();
})();
