# Arabiska ordkort, källfiler

Här ligger allt som appen och utskriften byggs från.

| Fil | Vad det är |
|---|---|
| `template.html` | Appen: utseende och all kod. Orden stoppas in där det står `__WORDS__`. |
| `data/ord.json` | Alla 370 ord med libanesiska, irakiska och standardarabiska. Här ändrar du ord. |
| `bygg.py` | Bygger `../index.html` (alla dialekter), `../ord.json` och dialektsidorna `../libanesiska/`, `../irakiska/` och `../standardarabiska/`. |
| `gen_print.py`, `pdf.js` | Gör utskrifts-PDF:en. |
| `fonts/` | Typsnitten som bakas in i utskriften. |
| `data/*.tsv` | Råmaterial: ordlistan från böckerna (`list.tsv`, `lessons345.tsv`), irakiska former (`irq.tsv`) och jag-former för verb (`verbs_jag.tsv`). Behövs inte för att bygga. |

## Bygga appen

```
python bygg.py
```

## Göra utskrifts-PDF:en

Kräver Node och Playwright (`npm install playwright` och `npx playwright install chromium`).

```
python gen_print.py book
node pdf.js book
```

Det ger `print_book.pdf`. Byt `book` mot `din` eller `arabizi` för andra transkriptioner.

## Ett ord i data/ord.json

```json
{"sv": "bok", "pos": "noun", "t": "Möbler & föremål",
 "msa": {"f": [["كِتاب", "kitāb"], ["كُتُب", "kutub"]], "n": "", "s": "Standard lektion 1"},
 "leb": {"f": [["كتاب", "ktaab"], ["كتب", "kutub"]], "n": ""},
 "irq": {"f": [["كتاب", "ktaab"], ["كتب", "kutub"]], "n": ""}}
```

`f` är formerna (arabiska, transkription): singular och plural, eller för verb dåtid han, dåtid jag och nutid jag. `n` är en anmärkning och `s` vilket kapitel ordet kommer från. Transkriptionen skrivs i bokens stil. Appen räknar själv om den till DIN och Arabizi.
