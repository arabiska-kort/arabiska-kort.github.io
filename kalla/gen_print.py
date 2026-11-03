import base64, sys, re
sys_ = sys.argv[1]  # din | arabizi
F = 'fonts/'
def ff(name, path, w):
    b = base64.b64encode(open(F+path,'rb').read()).decode()
    return f"@font-face{{font-family:'{name}';font-weight:{w};src:url(data:font/woff2;base64,{b}) format('woff2');}}"
faces = ''.join([
  ff('AR','noto-naskh-arabic-arabic-700-normal.woff2',700),
  ff('UI','figtree-latin-400-normal.woff2',400),
  ff('UIX','figtree-latin-ext-400-normal.woff2',400),
  ff('UI','figtree-latin-700-normal.woff2',700),
  ff('UIX','figtree-latin-ext-700-normal.woff2',700),
  ff('UI','figtree-latin-800-normal.woff2',800),
  ff('UIX','figtree-latin-ext-800-normal.woff2',800),
])
tpl = open('template.html', encoding='utf-8').read()
js = tpl[tpl.index('function rep('):tpl.index('// --- Val av kort')]
words = open('data/ord.json', encoding='utf-8').read()
html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
{faces}
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; }}
body {{ font-family: UI, UIX, 'DejaVu Sans', sans-serif; color: #17202B; }}
.sheet {{ width: 210mm; height: 297mm; display: grid; grid-template-columns: repeat(3, 63mm); grid-auto-rows: 88mm;
  justify-content: center; align-content: center; page-break-after: always; }}
.cell {{ position: relative; outline: 0.2mm dashed #C9CFD8; outline-offset: -0.1mm; padding: 2.5mm; }}
.card {{ --c: #1F5FD1; height: 100%; border: 1.6mm solid var(--c); border-radius: 4mm; padding: 3mm 3.2mm; display: flex; flex-direction: column; overflow: hidden; }}
.verb {{ --c: #D9650B; }} .prep {{ --c: #B02A78; }} .other {{ --c: #5E6B7D; }} .adj {{ --c: #2E7D3E; }} .pron {{ --c: #6A4BC4; }} .q {{ --c: #946A00; }}
.top {{ display: flex; justify-content: space-between; font-size: 2.5mm; }}
.pos {{ font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--c); }}
.side {{ color: #5B6676; }}
.sv {{ flex: 1; display: flex; align-items: center; justify-content: center; text-align: center; font-weight: 800; font-size: 7mm; line-height: 1.15; overflow-wrap: anywhere; }}
.sub {{ text-align: center; color: #5B6676; font-size: 2.8mm; line-height: 1.4; }}
.word {{ font-weight: 800; font-size: 3.6mm; margin: 1.2mm 0 1.6mm; }}
.dl {{ display: flex; justify-content: space-between; font-size: 2.1mm; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: #5B6676; border-bottom: 0.25mm solid #D6DCE4; padding-bottom: .6mm; }}
.dl em {{ font-style: normal; font-weight: 400; letter-spacing: 0; text-transform: none; }}
.leb .dl, .msa .dl {{ color: var(--c); }}
.msa {{ margin-top: 2mm; }}
.row {{ display: flex; justify-content: space-between; align-items: center; gap: 1.5mm; padding: .9mm 0; border-bottom: 0.2mm solid #E6EAF0; }}
.row:last-child {{ border-bottom: 0; }}
.l {{ display: flex; flex-direction: column; min-width: 21mm; flex-shrink: 1; }}
.k {{ font-weight: 700; font-size: 2.5mm; }}
.vem {{ font-weight: 400; }}
.tr {{ font-style: italic; color: #5B6676; font-size: 2.8mm; overflow-wrap: anywhere; }}
.ar {{ flex-shrink: 0; font-family: AR, 'FreeSerif', serif; font-weight: 700; direction: rtl; white-space: nowrap; line-height: 1.35; }}
.leb .ar, .msa .ar {{ font-size: 5.4mm; }}
.vg {{ display: grid; grid-template-columns: 10mm 1fr 1fr; column-gap: 1.5mm; align-items: center; }}
.vh {{ font-weight: 700; font-size: 2.3mm; color: #5B6676; text-align: center; padding-top: .6mm; }}
.vk {{ font-weight: 700; font-size: 2.5mm; }}
.vc {{ min-width: 0; display: flex; flex-direction: column; align-items: center; text-align: center; padding: .6mm 0; border-bottom: 0.2mm solid #E6EAF0; }}
.vg .vc:last-child, .vg .vc:nth-last-child(2) {{ border-bottom: 0; }}
.leb .vc .ar, .msa .vc .ar {{ font-size: 4.8mm; }}
.vc .tr {{ font-size: 2.5mm; }}
.ayn {{ font-style: normal; font-weight: 500; font-size: 0.8em; line-height: 0; vertical-align: 0.4em; display: inline-block; margin: 0 0.06em; }}
.ayn.hz {{ transform: scaleX(-1); }}
.note {{ font-size: 2.1mm; color: #5B6676; padding-top: .6mm; }}
</style></head><body><div id="out"></div><script>
const WORDS = {words};
{js}
const SYS = "{sys_}";
const POS = {{ noun: "Substantiv", prep: "Preposition", verb: "Verb", adj: "Adjektiv", pron: "Pronomen", q: "Frågeord", other: "Fras" }};
const ORDER = {{ noun: 0, verb: 1, adj: 2, prep: 3, pron: 4, q: 5, other: 6 }};
const esc = t => String(t).replace(/[&<>]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;"}})[c]);
const cards = WORDS.slice().sort((a, b) => ORDER[a.pos] - ORDER[b.pos] || a.t.localeCompare(b.t, "sv") || a.sv.localeCompare(b.sv, "sv"));
function block(w, key, name) {{
  const d = w[key];
  const rows = d.f.map(([ar, tr], k) => `<div class="row"><div class="l">${{d.f.length > 1 ? `<span class="k">${{w.pos === "verb" ? (d.f.length === 3 ? ["Dåtid", "Dåtid", "Nutid"] : ["Dåtid", "Nutid"])[k] + ' (<span class="vem">' + (d.f.length === 3 && k ? "jag" : "han") + "</span>" + (w.b ? " " + w.b[k && (d.f.length === 3 ? k - 1 : k)] : "") + ")" : (k ? "Plural" : "Singular")}}</span>` : ""}}${{SYS !== "none" && tr ? `<span class="tr">${{esc(translit(tr, key, SYS)).replace(/[ʿʾ]/g, m => m === "ʿ" ? `<span class="ayn" title="ayn">c</span>` : `<span class="ayn hz" title="hamza">c</span>`)}}</span>` : ""}}</div><span class="ar">${{esc(ar)}}</span></div>`).join("");
  return `<div class="${{key}}"><div class="dl"><span>${{name}}</span>${{d.s ? `<em>${{esc(d.s)}}</em>` : ""}}</div>${{rows}}${{d.n ? `<div class="note">${{esc(d.n)}}</div>` : ""}}</div>`;
}}
const front = w => `<div class="card ${{w.pos}}"><div class="top"><span class="pos">${{POS[w.pos]}}</span><span class="side">Framsida</span></div><div class="sv">${{esc(w.sv)}}</div><div class="sub">${{esc(w.t)}}</div></div>`;
const back = w => `<div class="card ${{w.pos}}"><div class="top"><span class="pos">${{POS[w.pos]}}</span><span class="side">Baksida</span></div><div class="word">${{esc(w.sv)}}</div>${{block(w, "leb", "Libanesiska")}}${{block(w, "msa", "Standardarabiska")}}</div>`;
let html = "";
for (let p = 0; p < cards.length; p += 9) {{
  const page = cards.slice(p, p + 9);
  html += `<div class="sheet">${{page.map(w => `<div class="cell">${{front(w)}}</div>`).join("")}}</div>`;
  // Backs mirrored left-right per row, so they line up when printed double-sided (flip on long edge).
  const cells = [];
  for (let r = 0; r < 3; r++) for (let c = 2; c >= 0; c--) {{ const w = page[r * 3 + c]; cells.push(w ? `<div class="cell">${{back(w)}}</div>` : `<div class="cell" style="outline:0"></div>`); }}
  html += `<div class="sheet">${{cells.join("")}}</div>`;
}}
document.getElementById("out").innerHTML = html;
// Shrink any line that overflows its card.
document.fonts.ready.then(() => {{
  for (const el of document.querySelectorAll(".ar, .sv")) {{
    let s = parseFloat(getComputedStyle(el).fontSize), box = el.closest(".row") || el.parentElement;
    while (s > 6 && (box.scrollWidth > box.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2 && el.classList.contains("sv"))) {{ s *= 0.93; el.style.fontSize = s + "px"; }}
  }}
  for (const c of document.querySelectorAll(".card")) {{
    let g = 0; while (c.scrollHeight > c.clientHeight + 1 && g++ < 12) c.querySelectorAll(".ar").forEach(a => a.style.fontSize = parseFloat(getComputedStyle(a).fontSize) * 0.92 + "px");
  }}
  document.body.dataset.ready = 1;
}});
</script></body></html>'''
open(f'print_{sys_}.html','w', encoding='utf-8').write(html)
