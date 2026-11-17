// Bokens texter. Innehållet (texter.bin och ljud/*.bin) är krypterat och låses upp med
// användarnamn och lösenord. Nyckeln sparas i webbläsaren så att man bara loggar in en gång.
// SALT sätts av bygg_texter.py.
const ITER = 600000;
const NYCKEL_KEY = "texter-nyckel";
const VISA_KEY = "texter-visa";  // det man har slagit på under Visa (från början inget)
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
// [kod, namn, beskrivning, ordkortens sida]
const DIALEKTER = [
  ["msa", "Standardarabiska", "Texterna i lektion 2–6", "../standardarabiska/"],
  ["leb", "Libanesiska", "Dialogerna i Spoken Lebanese, kapitel 1, 10 och 11", "../libanesiska/"],
];
const dial = d => d.dialekt || "msa";
const LEB_NYCKEL = `Bokens transkription: <code>9</code> ʿayn · <code>'</code> hamza (kort stopp i halsen, ofta där
standardarabiskan har q) · <code>H</code> ح · <code>x</code> خ · <code>G</code> غ · <code>ʃ</code> sh ·
<code>S D T Z</code> de "tunga" ص ض ط ظ · dubbel vokal = lång vokal · dubbel konsonant = shadda ·
<code>*</code> före ett namn. Den arabiska skriften är tillagd och finns inte i boken.`;

// Adresser: #  = välj dialekt, #msa / #leb = dialektens lista, #kapitel2_text1 / #leb_kapitel10_text1 = en text.
function visa() {
  stopp();
  const id = location.hash.slice(1);
  const i = TEXTER.findIndex(d => namn(d) === id);
  if (i >= 0) visaText(i);
  else if (DIALEKTER.some(x => x[0] === id)) visaLista(id);
  else visaStart();
  window.scrollTo(0, 0);
}

function toprad(tillbakaText, tillbakaHref) {
  const top = el("div", "toprow");
  const back = el("a", "back", tillbakaText);
  back.href = tillbakaHref;
  const ut = el("button", "back", "Logga ut");
  ut.addEventListener("click", loggaUt);
  top.append(back, ut);
  app.append(top);
}

function visaStart() {
  document.title = "Texterna i boken";
  app.innerHTML = "";
  toprad("← Ordkorten", "../");
  app.append(html("header", null,
    '<p class="ar-title" lang="ar">النصوص</p><h1>Texterna i boken</h1>' +
    "<p>Texter och dialoger med uttal, ord för ord, svenska och bokens inspelningar.</p>"));
  const val = el("div", "dialval");
  for (const [kod, rubrik, under] of DIALEKTER) {
    const n = TEXTER.filter(d => dial(d) === kod).length;
    if (!n) continue;
    const a = el("a");
    a.href = "#" + kod;
    a.append(el("b", null, rubrik), el("span", null, `${under} · ${n} ${kod === "leb" ? "dialoger" : "texter"}`));
    val.append(a);
  }
  app.append(val);
}

function visaLista(kod) {
  const [, rubrik, under, ordkort] = DIALEKTER.find(x => x[0] === kod);
  document.title = rubrik + " – texter";
  app.innerHTML = "";
  toprad("← Ordkorten", ordkort);
  app.append(html("header", null, `<h1>${rubrik}</h1><p>${under}</p>`));
  const andra = DIALEKTER.find(x => x[0] !== kod);
  const byt = el("a", "back", `${andra[1]} →`);
  byt.href = "#" + andra[0];
  byt.style.marginTop = "14px";
  app.append(byt);
  const list = el("div", "list");
  let kap = null;
  for (const d of TEXTER.filter(d => dial(d) === kod)) {
    if (d.kapitel !== kap) { kap = d.kapitel; list.append(el("h2", null, "Kapitel " + kap)); }
    list.append(listRad(d));
  }
  app.append(list);
}

function listRad(d) {
  const a = el("a", "item");
  a.href = "#" + namn(d);
  const v = el("div");
  v.append(el("div", "sv-t", d.titel_sv),
    el("div", "meta", `${leb(d) ? "Dialog" : "Text"} ${d.text}${d.ljud ? " · 🔊 ljud" : ""} · ${d.intro}`));
  a.append(v);
  if (!leb(d)) {  // libanesiska har ingen arabisk titel i boken
    const ar = el("div", "ar-t", d.titel_ar);
    ar.lang = "ar";
    a.append(ar);
  }
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

// Knapparna under Visa: allt är av från början. En påslagen knapp sätter sin klass (show-…) på body.
function visaKnappar(controls) {
  let pa = store(() => JSON.parse(localStorage.getItem(VISA_KEY))) || [];
  controls.querySelectorAll(".toggle").forEach(btn => {
    const cls = btn.dataset.cls;
    const apply = () => {
      document.body.classList.toggle(cls, pa.includes(cls));
      btn.setAttribute("aria-pressed", String(pa.includes(cls)));
    };
    apply();
    btn.addEventListener("click", () => {
      pa = pa.includes(cls) ? pa.filter(c => c !== cls) : [...pa, cls];
      store(() => localStorage.setItem(VISA_KEY, JSON.stringify(pa)));
      apply();
    });
  });
}

function visaText(i) {
  const d = TEXTER[i];
  const samma = TEXTER.filter(x => dial(x) === dial(d));  // föregående/nästa inom samma dialekt
  const j0 = samma.indexOf(d), prev = samma[j0 - 1], nxt = samma[j0 + 1];
  const P = d.personer || [];
  const bok = d.ljud && d.ljud.bok;
  document.title = `${d.titel_sv} – kapitel ${d.kapitel}`;
  app.innerHTML = "";
  const back = el("a", "back", "☰ Alla texter");
  back.href = "#" + dial(d);
  app.append(back);

  const head = el("header");
  const latin = d.skrift === "latin";  // bokens text är en latinsk transkription (libanesiska)
  const art = el("p", "ar-title" + (latin ? " arx" : ""), d.titel_ar);
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

  const controls = html("div", "controls", '<span>Visa:</span>' +
    (latin ? '<button class="toggle" data-cls="show-ar">Arabiska</button>'
           : '<button class="toggle" data-cls="show-tr">Uttal</button>') +
    '<button class="toggle" data-cls="show-lit">Ord för ord</button><button class="toggle" data-cls="show-sv">Svenska</button>');
  controls.setAttribute("role", "group");
  app.append(controls);
  visaKnappar(controls);

  const dialog = el("div");
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
      // Standardarabiska: arabiskan stor och uttalet under. Libanesiska: bokens text stor,
      // och arabisk skrift under som bara visas när "Arabiska" är påslaget.
      const row = el("div", latin ? "lat-row" : "ar-row");
      const huvud = latin ? el("p", "lat", tr) : el("p", "ar", ar);
      if (!latin) huvud.lang = "ar";
      row.append(huvud);
      const tid = del.tider && del.tider[j];
      if (bok && tid) {
        const b = el("button", "play", "▶");
        b.title = "Lyssna";
        b.addEventListener("click", () => spelaBit(bok, tid[0], tid[1], line));
        row.append(b);
      }
      line.append(row);
      if (latin) { const a = el("p", "arx", ar); a.lang = "ar"; line.append(a); }
      else line.append(el("div", "tr", tr));
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
  m.href = "#" + dial(d);
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
