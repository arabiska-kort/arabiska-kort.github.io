"""Bygger bokens texter (standardarabiska) till ../texter/, krypterat.

Körs av bygg.py, eller själv i den här mappen:

    python bygg_texter.py

Källorna är privata och ligger i ../transkriptioner/ (som inte går upp till GitHub):
  data/kapitelN_textM.json   texterna (format: se nedan)
  ljud/bok_kapitelN_textM.mp3  bokens inspelningar
  inloggning.json            {"anvandare": "...", "losenord": "..."}

Ut kommer ../texter/index.html (en sida med inloggning), texter.bin och ljud/*.bin.
Allt innehåll krypteras med användarnamn och lösenord (kryptera.mjs, kräver Node),
så bokens texter och ljud ligger aldrig öppet på GitHub Pages.
Byter du lösenord: ändra inloggning.json och bygg om.

En datafil:
{
  "kapitel": 2, "text": 1, "titel_ar": "البيت", "titel_sv": "Huset", "intro": "Kort beskrivning.",
  "personer": [{"sv": "Muhammad", "ar": "محمّد"}],   (tom lista för löpande text)
  "ljud": {"bok": "ljud/bok_kapitel2_text1.mp3"},     (valfritt)
  "delar": [{"vem": 0, "bok": "texten som i boken",
             "rader": [["arabiska med vokaler", "uttal", "ord för ord", "svenska"]],
             "tider": [[start, slut]]}],              (sekunder i bokens inspelning, valfritt)
  "tips": [{"h": "Rubrik", "ar": "arabiska", "p": "Förklaring (HTML går bra)"}]
}
"""
import glob, json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "texter")

CSS = r"""
:root {
  --bg: #f6f3ee; --card: #ffffff; --text: #1f1d1a; --muted: #6b665e; --line: #e4ded4;
  --p0: #1f6f8b; --p0-bg: #e6f2f6; --p1: #a2475e; --p1-bg: #f8e9ed; --p2: #4f7a3a; --p2-bg: #ebf3e5;
  --prose: #8a6a2f; --prose-bg: #f5ecd9; --accent: #b5832a;
  --font-ui: Figtree, system-ui, sans-serif; --font-ar: "Noto Naskh Arabic", "Arial", serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #171614; --card: #22201d; --text: #ece8e1; --muted: #a39d93; --line: #36322d;
    --p0: #7cc3dc; --p0-bg: #1c2e35; --p1: #e59bb0; --p1-bg: #3a2229; --p2: #a5d18b; --p2-bg: #24301d;
    --prose: #e0b25c; --prose-bg: #352b19; --accent: #e0b25c;
  }
}
:root[data-theme="dark"] {
  --bg: #171614; --card: #22201d; --text: #ece8e1; --muted: #a39d93; --line: #36322d;
  --p0: #7cc3dc; --p0-bg: #1c2e35; --p1: #e59bb0; --p1-bg: #3a2229; --p2: #a5d18b; --p2-bg: #24301d;
  --prose: #e0b25c; --prose-bg: #352b19; --accent: #e0b25c;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--font-ui); line-height: 1.5; }
main { max-width: 760px; margin: 0 auto; padding: 32px 16px 80px; }
a { color: var(--accent); }
.back { font-size: .9rem; text-decoration: none; }
header h1 { margin: 0; font-size: 1.9rem; font-weight: 800; }
header .ar-title { font-family: var(--font-ar); font-size: 2.6rem; line-height: 1.6; margin: 8px 0 0; direction: rtl; }
header p { color: var(--muted); margin: 6px 0 0; }
.audio { display: flex; flex-wrap: wrap; gap: 12px 20px; margin-top: 14px; }
.audio label { font-size: .85rem; color: var(--muted); display: block; }
.audio audio { height: 36px; max-width: 100%; }
.controls {
  position: sticky; top: 0; z-index: 5; background: var(--bg); padding: 14px 0; margin: 20px 0 8px;
  border-bottom: 1px solid var(--line); display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
}
.controls span { color: var(--muted); font-size: .9rem; margin-right: 4px; }
.toggle {
  font: inherit; font-size: .9rem; font-weight: 600; border: 1px solid var(--line); background: var(--card);
  color: var(--text); padding: 6px 14px; border-radius: 999px; cursor: pointer;
}
.toggle[aria-pressed="true"] { background: var(--text); color: var(--bg); border-color: var(--text); }
.turn {
  background: var(--card); border: 1px solid var(--line); border-left: 5px solid var(--who);
  border-radius: 14px; padding: 16px 20px; margin: 14px 0;
}
.turn.p0 { --who: var(--p0); --who-bg: var(--p0-bg); }
.turn.p1 { --who: var(--p1); --who-bg: var(--p1-bg); }
.turn.p2 { --who: var(--p2); --who-bg: var(--p2-bg); }
.turn.prose { --who: var(--prose); --who-bg: var(--prose-bg); }
.who {
  display: inline-block; font-size: .8rem; font-weight: 800; letter-spacing: .04em; text-transform: uppercase;
  color: var(--who); background: var(--who-bg); padding: 2px 10px; border-radius: 999px;
}
.who .num { opacity: .6; margin-right: 4px; }
.line + .line { margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--line); }
.ar-row { display: flex; align-items: center; gap: 10px; justify-content: flex-end; }
.ar { font-family: var(--font-ar); font-size: 1.9rem; line-height: 2; direction: rtl; text-align: right; margin: 6px 0 2px; }
.play {
  flex: none; width: 34px; height: 34px; border-radius: 50%; border: 1px solid var(--line);
  background: var(--card); color: var(--who); cursor: pointer; font-size: .9rem;
}
.play.alt { font-size: .75rem; font-weight: 800; color: var(--muted); }
.line.playing .ar { color: var(--who); }
.tr { color: var(--accent); font-style: italic; font-size: 1.02rem; }
.lit { color: var(--muted); font-size: .95rem; }
.lit::before { content: "ord för ord: "; font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; }
.sv { font-weight: 600; font-size: 1.12rem; margin-top: 4px; }
.hide-tr .tr, .hide-lit .lit, .hide-sv .sv { display: none; }
section.extra { margin-top: 48px; }
section.extra h2 { font-size: 1.35rem; font-weight: 800; margin: 0 0 12px; }
.tips { display: grid; gap: 12px; }
.tip { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px 18px; }
.tip h3 { margin: 0 0 4px; font-size: 1rem; }
.tip .ar-inline { font-family: var(--font-ar); font-size: 1.35rem; direction: rtl; unicode-bidi: isolate; }
.tip p { margin: 4px 0 0; color: var(--muted); }
details { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px 18px; margin: 12px 0; }
summary { font-weight: 800; cursor: pointer; }
.full-ar { font-family: var(--font-ar); font-size: 1.45rem; line-height: 2.1; direction: rtl; text-align: right; }
.full-ar p, .full-sv p { margin: 6px 0; }
.full-sv b { font-size: .9rem; }
.full-ar b { font-size: 1.2rem; }
.key { color: var(--muted); font-size: .92rem; }
.key code { font-family: inherit; font-weight: 700; color: var(--text); }
footer {
  margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--line); font-size: .95rem; font-weight: 600;
  display: grid; grid-template-columns: 1fr auto 1fr; gap: 12px; align-items: center;
}
footer a { text-decoration: none; }
footer .alla {
  color: var(--text); border: 1px solid var(--line); background: var(--card); border-radius: 999px; padding: 6px 14px;
}
footer .next { text-align: right; }
.back {
  display: inline-block; color: var(--text); font-weight: 600; border: 1px solid var(--line);
  background: var(--card); border-radius: 999px; padding: 4px 12px;
}
@media (max-width: 520px) {
  footer { grid-template-columns: 1fr 1fr; }
  footer .alla { grid-column: 1 / -1; grid-row: 1; justify-self: center; }
}
.list { display: grid; gap: 12px; margin-top: 24px; }
.list h2 { font-size: 1.1rem; margin: 18px 0 0; color: var(--muted); font-weight: 800; }
.item {
  display: flex; justify-content: space-between; align-items: center; gap: 12px; text-decoration: none; color: var(--text);
  background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px 20px;
}
.item:hover { border-color: var(--accent); }
.item .sv-t { font-weight: 700; font-size: 1.1rem; }
.item .meta { color: var(--muted); font-size: .85rem; }
.item .ar-t { font-family: var(--font-ar); font-size: 1.7rem; direction: rtl; white-space: nowrap; flex: none; }
@media (max-width: 520px) {
  .ar { font-size: 1.6rem; }
  header .ar-title { font-size: 2.2rem; }
  .turn { padding: 14px; }
}
"""

KEY = """<code>ʾ</code> hamza (kort stopp i halsen) · <code>ʿ</code> ʿayn · <code>ḥ</code> ح · <code>kh</code> خ ·
<code>dh</code> ذ · <code>th</code> ث · <code>gh</code> غ · <code>sh</code> ش · <code>ṣ ḍ ṭ ẓ</code> de "tunga" ص ض ط ظ ·
<code>ā ī ū</code> långa vokaler · dubbel konsonant = shadda. Det inom parentes är formella ändelser som man
oftast hoppar över i tal."""

LOGIN_CSS = r"""
.toprow { display: flex; justify-content: space-between; gap: 12px; }
button.back { font: inherit; font-size: .9rem; cursor: pointer; }
.login { max-width: 380px; margin: 40px auto 0; display: grid; gap: 14px; }
.login h1 { margin: 0; font-size: 1.9rem; font-weight: 800; }
.login .ar-title { font-family: var(--font-ar); font-size: 2.4rem; line-height: 1.5; margin: 0; direction: rtl; text-align: right; }
.login .muted { color: var(--muted); margin: 0; }
.login label { display: grid; gap: 6px; font-weight: 600; font-size: .9rem; }
.login input {
  font: inherit; font-size: 1rem; padding: 10px 12px; border-radius: 10px;
  border: 1.5px solid var(--line); background: var(--card); color: var(--text);
}
.login button {
  font: inherit; font-weight: 700; padding: 11px; border-radius: 10px; border: 0;
  background: var(--text); color: var(--bg); cursor: pointer;
}
.login button:disabled { opacity: .6; cursor: wait; }
.login .fel { color: #c0392b; margin: 0; min-height: 1.2em; font-weight: 600; }
.full-lat { font-size: 1.08rem; line-height: 1.8; }
.full-lat p { margin: 6px 0; }
.list h2.dial { font-size: 1.5rem; color: var(--text); margin: 32px 0 0; }
.list h2.dial:first-child { margin-top: 8px; }
.list h2.dial small { font-size: .85rem; color: var(--muted); font-weight: 600; margin-left: 8px; }
"""

SHELL = """<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Texterna i boken</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;800&family=Noto+Naskh+Arabic:wght@400;600&display=swap" rel="stylesheet">
<style>__CSS__</style>
</head>
<body>
<main id="app"></main>
<script>
const SALT = "__SALT__";
const UTTALSNYCKEL = __KEY__;
__APP__
</script>
</body>
</html>
"""

# Fast salt: samma lösenord ger samma nyckel, så oförändrade filer blir likadana vid nästa bygge.
SALT = "Pq2bJ0r7v6m1yQ3sXk8dZg=="


def main():
    privat = os.path.join(HERE, "..", "transkriptioner")
    data_dir, ljud_dir = os.path.join(privat, "data"), os.path.join(privat, "ljud")
    login_fil = os.path.join(privat, "inloggning.json")
    filer = glob.glob(os.path.join(data_dir, "*kapitel*_text*.json"))
    if not os.path.exists(login_fil) or not filer:
        print("Texterna: hoppar över (ingen transkriptioner/data eller inloggning.json här)")
        return
    login = json.load(open(login_fil, encoding="utf-8"))

    texter = []
    for f in filer:
        with open(f, encoding="utf-8") as fh:
            texter.append(json.load(fh))
    # Standardarabiska först, sedan libanesiska.
    texter.sort(key=lambda d: (d.get("dialekt", "msa") == "leb", d["kapitel"], d["text"]))

    os.makedirs(os.path.join(OUT, "ljud"), exist_ok=True)
    par = {}  # ljudfil -> krypterad fil (samma fil kan delas av flera dialoger)
    for d in texter:
        d.pop("kalla", None)
        for de in d["delar"]:
            for r in de["rader"]:
                del r[4:]  # gamla datorröstfiler används inte här
        bok = (d.get("ljud") or {}).get("bok")
        if bok:
            src = os.path.join(ljud_dir, os.path.basename(bok))
            ut = "ljud/" + os.path.splitext(os.path.basename(bok))[0] + ".bin"
            par[src] = os.path.join(OUT, ut)
            d["ljud"] = {"bok": ut}
            # Spelaren för hela texten spelar bara den här dialogens del av inspelningen.
            tider = [t for de in d["delar"] for t in de.get("tider", [])]
            if tider:
                d["ljud"]["omrade"] = [tider[0][0], tider[-1][1]]
        else:
            d.pop("ljud", None)
    par = list(par.items())

    tmp = os.path.join(HERE, "__pycache__", "texter.json")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(texter, fh, ensure_ascii=False, separators=(",", ":"))
    par.insert(0, (tmp, os.path.join(OUT, "texter.bin")))

    env = dict(os.environ, TEXTER_ANV=login["anvandare"], TEXTER_LOSEN=login["losenord"])
    args = ["node", os.path.join(HERE, "kryptera.mjs"), SALT] + [x for p in par for x in p]
    subprocess.run(args, check=True, env=env)
    os.remove(tmp)

    app_js = open(os.path.join(HERE, "texter_app.js"), encoding="utf-8").read()
    page = (SHELL.replace("__CSS__", CSS + LOGIN_CSS).replace("__SALT__", SALT)
            .replace("__KEY__", json.dumps(KEY, ensure_ascii=False)).replace("__APP__", app_js))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    rader = sum(len(x["rader"]) for d in texter for x in d["delar"])
    print(f"Texterna: ../texter/ ({len(texter)} texter, {rader} rader, {len(par) - 1} ljudfiler, krypterat)")


if __name__ == "__main__":
    main()
