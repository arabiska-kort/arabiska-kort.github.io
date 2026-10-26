"""Bygger appen från template.html och data/ord.json.

Kör i den här mappen:

    python bygg.py

Resultatet hamnar i ../index.html (alla dialekter) och ../ord.json, och i
../libanesiska/ och ../standardarabiska/ med bara en dialekt. Irakiska finns bara på huvudsidan.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
WEBB = os.path.join(HERE, "..")

tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
words = open(os.path.join(HERE, "data", "ord.json"), encoding="utf-8").read().strip()
os.makedirs(WEBB, exist_ok=True)
# Mapp och låst dialekt för varje sida. Huvudsidan har alla.
SIDOR = {"": None, "libanesiska": "leb", "standardarabiska": "msa"}
for mapp, dialekt in SIDOR.items():
    os.makedirs(os.path.join(WEBB, mapp), exist_ok=True)
    with open(os.path.join(WEBB, mapp, "index.html"), "w", encoding="utf-8") as f:
        f.write(tpl.replace("__LOCK__", json.dumps(dialekt)).replace("__WORDS__", words))
shutil.copyfile(os.path.join(HERE, "data", "ord.json"), os.path.join(WEBB, "ord.json"))
print("Klart: ../index.html, ../libanesiska/, ../standardarabiska/")

