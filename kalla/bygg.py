"""Bygger appen från template.html och data/ord.json.

Kör i den här mappen:

    python bygg.py

Startsidan start.html kopieras till ../index.html. Appen hamnar i ../alla/ (alla dialekter)
och i ../libanesiska/ och ../standardarabiska/ med bara en dialekt. Irakiska finns bara i alla/.
Finns firebase-config.json får korten en felanmälan och fel.html blir ../fel/.
Orden kopieras också till ../ord.json, som skapa_ljud.py läser.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
WEBB = os.path.join(HERE, "..")

tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
words = open(os.path.join(HERE, "data", "ord.json"), encoding="utf-8").read().strip()
# Firebase-projektet för felanmälningar. Utan filen visas ingen felanmälan och ingen fel-sida.
cfg = os.path.join(HERE, "firebase-config.json")
firebase = open(cfg, encoding="utf-8").read().strip() if os.path.exists(cfg) else "null"
tpl = tpl.replace("__FIREBASE__", firebase)
os.makedirs(WEBB, exist_ok=True)
# Mapp och låst dialekt för varje sida.
SIDOR = {"alla": None, "libanesiska": "leb", "standardarabiska": "msa"}
for mapp, dialekt in SIDOR.items():
    os.makedirs(os.path.join(WEBB, mapp), exist_ok=True)
    with open(os.path.join(WEBB, mapp, "index.html"), "w", encoding="utf-8") as f:
        f.write(tpl.replace("__LOCK__", json.dumps(dialekt)).replace("__WORDS__", words))
shutil.copyfile(os.path.join(HERE, "start.html"), os.path.join(WEBB, "index.html"))
if firebase != "null":
    os.makedirs(os.path.join(WEBB, "fel"), exist_ok=True)
    with open(os.path.join(WEBB, "fel", "index.html"), "w", encoding="utf-8") as f:
        f.write(open(os.path.join(HERE, "fel.html"), encoding="utf-8").read().replace("__FIREBASE__", firebase))
shutil.copyfile(os.path.join(HERE, "data", "ord.json"), os.path.join(WEBB, "ord.json"))
print("Klart: ../index.html (start), ../alla/, ../libanesiska/, ../standardarabiska/")

# Bokens texter (standardarabiska) i ../texter/
import bygg_texter
bygg_texter.main()

