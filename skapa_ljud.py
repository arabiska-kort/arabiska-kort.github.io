"""Skapar ljudfiler för ordkorten med Azures talsyntes.

Kör i den här mappen (där index.html och ord.json ligger):

    python skapa_ljud.py

Skriptet frågar efter nyckel och region från Azure (Speech-resursen, "Nycklar och slutpunkt").
Du kan också sätta dem som miljövariabler AZURE_SPEECH_KEY och AZURE_SPEECH_REGION.

Filerna hamnar i mappen ljud/ tillsammans med ljud/index.json, som appen läser.
Gratisnivån tillåter 20 anrop i minuten, så första körningen tar ungefär en timme.
Avbryter du och kör igen fortsätter skriptet där det slutade.

Lägg till --man för manliga röster.
"""
import array, getpass, hashlib, io, json, os, re, sys, time, urllib.error, urllib.request, wave
from functools import lru_cache
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ljud")
VOICES = {
    False: {"leb": ("ar-LB", "ar-LB-LaylaNeural"), "irq": ("ar-IQ", "ar-IQ-RanaNeural"), "msa": ("ar-SA", "ar-SA-ZariyahNeural")},
    True: {"leb": ("ar-LB", "ar-LB-RamiNeural"), "irq": ("ar-IQ", "ar-IQ-BasselNeural"), "msa": ("ar-SA", "ar-SA-HamedNeural")},
}
# Libanesiska och irakiska skrivs utan vokaltecken, så rösten får gissa (عرف kan bli
# ʿurf i stället för ʿirif). Skriptet sätter därför ut vokaltecken utifrån
# transkriptionen innan texten skickas till Azure. Kortet visar samma text som förut.
#
# Ord som ändå blir fel kan läggas in här: Azure får versionen till höger.
# Ett "|långsam" sist läser ordet långsammare. Ett "|sista" sparar bara sista ordet: skriv ordet
# två gånger, så låter det andra ofta tydligare. Ett "|mening" läser ordet sist i en kort mening,
# "al-baytu ...", och sparar bara ordet (ensamt fick وَسِخ ett o på slutet, sist i en mening inte).
# Ett "|ipa=..." ger rösten uttalet i ljudskrift (IPA) i stället för att den gissar från texten.
# Ett "|utan-slutvokal" klipper bort en vokal som lagts till sist, men behåller konsonanten före:
# تَرَكْتُو läses taraktu och sparas som tarakt (utan vokalen hördes inget t).
# Ändrar du här görs bara de filerna om.
UTTAL = {
    "leb|تعبان": "تَعْبان|långsam",   # trött: ayn hörs knappt
    "irq|تعبان": "تَعْبان|långsam",
    "msa|تَعْبان": "تَعْبان|långsam",
    # Sista bokstaven får inget sukun (med sukun lät rajul, bayt och saqf sämre), utom här, där
    # rösten annars lägger till en vokal (afkāro, shayn) eller tappar sista ljudet.
    "leb|أفكار": "أَفْكَارْ",   # idéer
    "irq|أفكار": "أَفْكَارْ",
    "msa|أَفْكار": "أَفْكارْ",
    "leb|أخبار": "أَخْبَارْ",   # nyheter: samma sak
    "irq|أخبار": "أَخْبَارْ",
    "msa|شَيْء": "شَيْءْ",   # sak: lät som shayn
    "msa|وَرَق": "وَرَقْ",   # papper
    "msa|أَوْراق": "أَوْراقْ",   # papper (plural): lät som awrāqu
    "msa|تَمام": "تَمامْ",   # bra, okej: lät som tamāmu
    "msa|مُعَلِّم": "مُعَلِّمْ",   # lärare: lät som muʿallimun
    "msa|مُعَلِّمون": "مُعَلِّمونْ",   # lärare (plural): lät som muʿallimūna
    "msa|يَسار": "يَسارْ",   # vänster: lät som yasāra
    "msa|إِلى اليَسار": "إِلى اليَسارْ",
    "msa|جِدار": "جِدارْ",   # vägg: lät som jidāron
    "msa|أُذُن": "أُذُنْ",   # öra: lät som udhunen
    "msa|طُرُق": "طُرُقْ",   # vägar: lät som ṭuruqu
    "msa|لُبْنان": "لُبْنانْ",   # Libanon: lät som lubnānu
    "msa|جُدُد": "جُدُدْ",   # nya: lät som jududi
    "msa|عُظَماء": "عُظَماءْ",   # storslagna: lät som ʿuẓamā't
    "msa|أَصْدِقاء": "أَصْدِقاءْ",   # samma t efter -ā' som i ʿuẓamā'
    "irq|أصدقاء": "أَصْدِقَاءْ",
    "msa|قُدَماء": "قُدَماءْ",
    "msa|نُظَفاء": "نُظَفاءْ",
    "msa|آباء": "آباءْ",
    "msa|أَطِبّاء": "أَطِبّاءْ",
    "msa|مَساء": "مَساءْ",
    "msa|سَماء": "سَماءْ",
    "msa|غَداء": "غَداءْ",
    "irq|أشياء": "أَشْيَاءْ",
    "msa|إِلى اللِّقاء": "إِلى اللِّقا",   # på återseende: t på slutet även med sukun, så utan hamza
    "msa|أَهالٍ": "أَهالِينْ",   # familjer: -in hördes inte, bara ahāl
    "msa|أَراضٍ": "أَراضِينْ",   # jord, mark: samma sak
    "msa|مُدُن": "مُدُونْ",   # städer: lät som mudunun, med sukun mudut
    "msa|لا بَأْس": "لا بَأْس|ipa=laː baʔs",   # inte illa: lät som lā ba'stso, med sukun lā ba'sts
    "msa|المَجَر": "المَجَر|ipa=ʔalmad͡ʒar",   # Ungern: lät som al-majara, även med sukun
    "msa|أَلْمانِيا": "أَلْمَانِيَا|långsam",   # Tyskland: rösten svalde l och ā
    "msa|جِدًّا": "جِدَّنْ",   # väldigt: med ًّا blev det jiddana
    "msa|وَسِخ": "وَسِخْ|mening",   # smutsig: ensamt lät det wasikho
    "msa|مَطْبَخ": "مَطْبَخْ|mening",   # kök: samma o efter kh
    "msa|مَطابِخ": "مَطابِخْ|mening",
    "msa|أَخ": "أَخْ|mening",   # bror
    "msa|كِبار": "كِبارْ|mening",   # stora: lät som kibārun
    "msa|شَهْر": "شَهْرْ|mening",   # månad: lät som shahrun
    "msa|طالِب": "طالِبْ|mening",   # student: ensamt lät b som t
    "msa|خَيْر": "خَيْر|mening",   # gott: ensamt fick r en vokal, med sukun försvann r
    "leb|وسخ": "وِسِخْ|mening",   # smutsig
    "leb|مطبخ": "مَطْبَخْ|mening",   # kök
    "leb|مطابخ": "مَطَابِخْ|mening",
    "irq|وصخ": "وُصِخْ|mening",   # smutsig
    "irq|مطبخ": "مَطْبَخْ|mening",   # kök
    "irq|مطابخ": "مَطَابُخْ|mening",
    "irq|مرّة لخ": "مَرّة لُخْ|mening",   # en gång till
    "msa|غَلَط": "غَلَطْ، غَلَطْ|sista",   # fel: ensamt hördes inte ṭ
    "leb|غلط": "غَلَطْ، غَلَطْ|sista",
    "msa|أُمّ": "أُومّ",   # mor: lät som emm
    "irq|أم": "أُومّ",
    "msa|كُرّاسة": "كُرّاسَهْ",   # skrivhäfte: med ة hördes inte -a
    "msa|في": "فِيي",   # i: lät som bara f
    "leb|في": "فِيي",   # det finns: samma sak
    "msa|شُهور": "شُهورْ",   # månader: lät som shuhūrun
    "msa|أَشْجار": "أَشْجارْ",   # träd: lät som ashjārun
    "msa|مُرَبّى": "مُرَبّى|ipa=murabbaː",   # marmelad: lät som murabb
    "msa|السّودان": "السّودانْ",   # Sudan: lät som as-sūdānu
    "msa|دِمَشْق": "دِمَشْق|ipa=dimaʃq",   # Damaskus: lät som dimashqa
    "msa|أَخْبار": "أَخْبار|ipa=ʔaxbaːr",   # nyheter: lät som akhbāru
    "msa|بَلَد": "بَلَدْ",   # land: lät som baladin
    "msa|بُلْدان": "بُلْدانْ",   # länder: lät som buldānun
    "msa|قَلَم": "قَلَمْ",   # penna: utan sukun fick m en vokal efter sig
    "leb|ولد": "وَلَدْ",   # barn: lät som walad med kasusändelse
    "leb|حجر": "حَجَرْ",   # sten: lät som Hajar med kasusändelse
    "leb|بمرق": "بِمْرُؤْ",   # jag går förbi: med q lät det bimru't
    "leb|دار": "دارْ",   # vardagsrum: lät som daari
    "leb|مغسلة": "مَغْسَلِه",   # handfat: med ة hördes inte -e
    "leb|وين هالغيبة": "وَيْن هالْغَيْبِه",   # var har du varit: med ة hördes inte -e
    "leb|خيّاط": "خِيّاطْ",   # skräddare: lät som xiyyaaTot
    "leb|بارك": "بارك|ipa=beːrak",   # gratulerade: utan vokaltecken gissade rösten fel
    "leb|مفتاح": "مفتاح|ipa=mifteːħ",   # nyckel: lät med o på slutet
    "leb|مفاتيح": "مْفاتِيحْ",   # nycklar: lät med o på slutet
    "leb|ثانويّة": "سَنَوِيِّه",   # gymnasium: med ة hördes inte -e
    "leb|حيّ": "حَيْ",   # kvarter: lät med o på slutet
    "leb|سخن": "سُخْنّْ|mening",   # varm: ensamt hördes inte x, dubbelt n så att n hörs
    "leb|يوم": "يَوْمْ",   # yawm: lät med en extra vokal på slutet
    "leb|فرن": "فُرْنْ",   # furn: lät med en extra vokal på slutet
    "leb|أجار": "أَجَارْ",   # ajaar: lät med en extra vokal på slutet
    "leb|محافظ": "محافظ|ipa=muħaːfizˤ",   # muHaafiZ: lät med en extra vokal på slutet
    "leb|بلّاط": "بُلَّاطْ",   # bullaaT: lät med en extra vokal på slutet
    "leb|تخصّص": "تخصّصْ",   # txaSSaS: lät med en extra vokal på slutet
    "leb|مقطوع": "مَقْطُوعْ",   # ma'Tuu9: lät med en extra vokal på slutet
    "leb|كلّك ذوق": "كِلِّك ذَوْقْ",   # killik zaw': lät med en extra vokal på slutet
    "leb|كتّاب": "كِتَّابْ",   # kittaab: lät med en extra vokal på slutet
    "leb|صحاب": "صحَابْ",   # SHaab: lät med en extra vokal på slutet
    "leb|شوكة": "شَوْكِه",   # ʃawke: slutet (-e, -i, -a) hördes inte
    "leb|فرشة": "فَرْشِه",   # farʃe: slutet (-e, -i, -a) hördes inte
    "leb|مكنسة": "مِكِنْسِه",   # miknse: slutet hördes inte, och utan i mellan k och n hördes inget s
    "leb|فرشاية": "فرشايِه",   # firʃeeye: slutet (-e, -i, -a) hördes inte
    "leb|حنفيّة": "حَنَفِيِّه",   # Hanafiyye: slutet (-e, -i, -a) hördes inte
    "leb|غيبة": "غَيْبِه",   # Gaybe: slutet (-e, -i, -a) hördes inte
    "leb|شقّة": "شِقَّه",   # ʃi''a: slutet (-e, -i, -a) hördes inte
    "leb|مثل ما شايفة": "مثل ما شايفِه",   # mitl ma ʃeeyfe: slutet (-e, -i, -a) hördes inte
    "leb|محامية": "مُحَامِيِّه",   # muHamiyyi: slutet (-e, -i, -a) hördes inte
    "leb|كهربجيّة": "كِهْرَبْجِيِّه",   # kihrabjiyyi: slutet (-e, -i, -a) hördes inte
    "leb|شوك": "شُوَكْ",   # ʃuwak: rösten läste fel ord
    "leb|تهنّى": "تْهَنّى",   # thanna: rösten läste fel ord
    "leb|مش ماشي": "مِشْ ماشِي",   # miʃ meeʃi: rösten läste fel ord
    "leb|تخت": "تَخْتْ|mening",   # säng: ensamt lät det som ett annat ord
    "leb|تركت": "تَرَكْتُو|utan-slutvokal",   # jag lämnade: utan vokalen efter hördes inget t
    "leb|سقف": "سَأْف",   # sa'f: ق ska vara stötljud, inte q
    "leb|سقوف": "سؤُوف",   # s'uuf: ق ska vara stötljud, inte q
    "leb|حلّاق": "حلّاأ",   # Hillee': ق ska vara stötljud, inte q
    "leb|موسيقار": "مُوسِيأَار",   # musi'aar: ق ska vara stötljud, inte q
    "leb|قنصل": "ؤُنْصُل",   # 'unSul: ق ska vara stötljud, inte q
    "leb|قاضي": "أَاضِي",   # 'aaDi: ق ska vara stötljud, inte q
    "leb|قدّم": "أَدَّم",   # 'addam: ق ska vara stötljud, inte q
    "leb|قدّمت": "أَدَّمْت",   # 'addamt: ق ska vara stötljud, inte q
    "leb|بقدّم": "بأَدِّم",   # b'addim: ق ska vara stötljud, inte q
    "leb|طابق": "طَابِئ",   # Taabi': ق ska vara stötljud, inte q
    "leb|طوابق": "طوَابِئ",   # Twaabi': ق ska vara stötljud, inte q
    "leb|شقق": "شِئَأ",   # ʃi'a': ق ska vara stötljud, inte q
    "leb|ورق تواليت": "وَرَأ توَاليت",   # wara' twaleet: ق ska vara stötljud, inte q
    "leb|ملعقة": "مَلْعْأة",   # mal9'a: ق ska vara stötljud, inte q
    "leb|ناقصو": "نَاأْصُو",   # naa'Su: ق ska vara stötljud, inte q
    "leb|وقّف": "وَأَّف",   # wa''af: ق ska vara stötljud, inte q
    "leb|وقّفت": "وَأَّفْت",   # wa''aft: ق ska vara stötljud, inte q
    "leb|بوقّف": "بوَئِّف",   # bwa''if: ق ska vara stötljud, inte q
    "leb|مرق": "مَرَأ",   # mara': ق ska vara stötljud, inte q
    "leb|مرقت": "مَرَأْت",   # mara't: ق ska vara stötljud, inte q
    "leb|قعد": "أَعَدْ",   # 'a9ad: ق ska vara stötljud, sukun så att inget o hörs
    "leb|قعدت": "أَعَدْت",   # 'a9adt: ق ska vara stötljud, inte q
    "leb|بقعد": "بِئْعُد",   # bi'9ud: ق ska vara stötljud, inte q
    "leb|اتّفق": "اتَّفَأ",   # ttafa': ق ska vara stötljud, inte q
    "leb|اتّفقت": "اتَّفَأْت",   # ttafa't: ق ska vara stötljud, inte q
    "leb|بتّفق": "بِتِّفِئ",   # bittifi': ق ska vara stötljud, inte q
    "leb|شوي": "شْوَيْ",   # lite: lät som shuway
    "leb|بعد شوي": "بَعْد شْوَيْ",   # senare: lät som ba9d shuway
    "leb|نجّار": "نِجّارْ",   # snickare: lät som nijjaaron
    "leb|هالسنة": "هَسِّنِه",   # i år: med l lät det hal-esna, skrivet som det uttalas
    "leb|شركة": "شِرْكِه",   # företag: med ة lät det ʃirka
    "leb|شرك": "شِرَكْ",   # företag (pl.): lät med o på slutet
    "leb|كيفك؟": "كِيفَك؟ كِيفِك؟",   # hur mår du: båda formerna, kiifak (till en man) och kiifik (till en kvinna)
    "msa|وَالله": "وَاللّٰهِي",   # vid Gud: utan vokal blev det wallāh, kortet säger wa-llāhi
}
PAUSE = 3.2  # sekunder mellan anrop, för gratisnivåns gräns på 20 anrop i minuten


FATHA, KASRA, DAMMA, SUKUN, SHADDA = "َ", "ِ", "ُ", "ْ", "ّ"
MARKS = re.compile("[ً-ْٰـ]")

# Arabisk bokstav -> konsonanter i transkriptionen som den kan stå för.
CONS = {
    "ب": "b p", "ت": "t", "ث": "þ t s", "ج": "j", "ح": "H", "خ": "x", "د": "d", "ذ": "ð d z",
    "ر": "r", "ز": "z", "س": "s", "ش": "ʃ", "ص": "S s", "ض": "D Ð", "ط": "T t", "ظ": "Z Ð D z",
    "ع": "9", "غ": "G", "ف": "f v", "ق": "q ' g", "ك": "k č g", "ل": "l", "م": "m", "ن": "n",
    "ه": "h", "و": "w", "ي": "y", "گ": "g", "چ": "č", "پ": "p b", "ء": "'", "أ": "'", "إ": "'",
    "ؤ": "'", "ئ": "' y", "آ": "'",
}
CONS = {k: set(v.split()) for k, v in CONS.items()}
SHORT = {"a": FATHA, "i": KASRA, "u": DAMMA, "e": KASRA, "o": DAMMA}
LONG = {"ا": {"aa", "a"}, "ى": {"aa", "a"}, "و": {"uu", "oo", "u", "o"}, "ي": {"ii", "ee", "i", "e"}}


def tokens(tr, dialect):
    s = tr
    if dialect == "irq":
        s = s.replace("DH", "Ð").replace("dh", "ð").replace("th", "þ")
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c in "aeiou":
            if i + 1 < len(s) and s[i + 1] == c:
                out.append(("V", c + c)); i += 2; continue
            out.append(("v", c))
        elif c in " /":
            out.append(("sp", c))
        elif c == "-":
            pass  # bindestreck (il-bayt, is-salaame) skrivs inte på arabiska
        elif c in "?.!,":
            out.append(("p", c))
        else:
            out.append(("C", c))
        i += 1
    return out


def vocalize(ar, tr, dialect):
    """Sätter vokaltecken på arabiskan utifrån transkriptionen. None om de inte går att para ihop."""
    A = MARKS.sub("", ar)
    T = tokens(tr, dialect)

    @lru_cache(None)
    def go(i, j):
        # Hoppa över skiljetecken och bindestreck i transkriptionen.
        while j < len(T) and T[j][0] == "p":
            j += 1
        if i == len(A):
            return "" if j == len(T) else None
        L = A[i]
        if L in " /":
            if j < len(T) and T[j][0] == "sp":
                r = go(i + 1, j + 1)
                return None if r is None else L + r
            r = go(i + 1, j)
            return None if r is None else L + r
        if L in "؟،!?.":
            r = go(i + 1, j)
            return None if r is None else L + r
        opts = []
        # Konsonant, ev. dubbel (shadda), följd av kort vokal eller ingen vokal.
        if L in CONS and j < len(T) and T[j][0] == "C" and T[j][1] in CONS[L]:
            k, mark = j + 1, ""
            if k < len(T) and T[k] == T[j] and not (i + 1 < len(A) and A[i + 1] == L):
                k += 1; mark = SHADDA
            if k < len(T) and T[k][0] == "v":
                # Kort vokal som ändå skrivs med lång bokstav, t.ex. sista -u i حلو (Hilu).
                if i + 1 < len(A) and A[i + 1] in LONG and T[k][1] in LONG[A[i + 1]]:
                    opts.append((mark + SHORT[T[k][1]], ("long", k)))
                # Före ة sätts ingen vokal: dialektrösten vet själv om det blir -a eller -e.
                before_ta = i + 1 < len(A) and A[i + 1] == "ة"
                opts.append((mark + ("" if before_ta else SHORT[T[k][1]]), k + 1))
            elif k < len(T) and T[k][0] == "V":
                long_ok = i + 1 < len(A) and A[i + 1] in LONG and T[k][1] in LONG[A[i + 1]]
                if long_ok:
                    v = T[k][1][0]
                    opts.append((mark + ({"a": FATHA, "i": KASRA, "u": DAMMA}.get(v, "")), ("long", k)))
            elif k < len(T) and T[k][0] == "C":
                # Ingen sukun på första bokstaven i ett ord (دروس, druus).
                first = i == 0 or A[i - 1] in " /"
                opts.append((mark + ("" if first else SUKUN), k))
            else:
                opts.append((mark, k))
        # Hamza i början av ordet som inte skrivs i transkriptionen (أنا = ana).
        if L in "أإآ" and j < len(T) and T[j][0] in ("v", "V"):
            v = T[j]
            if v[0] == "v":
                opts.append((SHORT[v[1]], j + 1))
            else:
                opts.append(("", ("long", j)) if L != "آ" else ("", j + 1))
        # Lång vokal som bokstav.
        if L in LONG and j < len(T) and T[j][0] in ("V", "v") and T[j][1] in LONG[L]:
            opts.append(("", j + 1))
        # و och ي som konsonant.
        # Alif i början (il-, al-) som läses som kort vokal eller inte alls.
        if L == "ا" and (i == 0 or A[i - 1] in " /"):
            if j < len(T) and T[j][0] == "v":
                opts.append(("", j + 1))
            opts.append(("", j))
        # ل i ال som har smält ihop med nästa bokstav (ish-shams).
        if L == "ل" and i > 0 and A[i - 1] == "ا" and (i == 1 or A[i - 2] in " /"):
            opts.append(("", j))
        # ة: -a, -e, -i eller -it/-at, eller ingenting.
        if L == "ة":
            if j < len(T) and T[j][0] == "v":
                if j + 1 < len(T) and T[j + 1] == ("C", "t"):
                    opts.append(("", j + 2))
                opts.append(("", j + 1))
            opts.append(("", j))
        # -an i slutet skrivs med alif (شكرا, ʃukran).
        if L == "ا" and j + 1 < len(T) and T[j] == ("v", "a") and T[j + 1] == ("C", "n") and (i + 1 == len(A) or A[i + 1] in " /؟،"):
            opts.append(("\u064b", j + 2))
        if L == "ا" and j < len(T) and T[j] == ("C", "n") and (i + 1 == len(A) or A[i + 1] in " /؟،"):
            opts.append(("\u064b", j + 1))
        # Alif efter و i pluralformer (كتبوا) läses inte.
        if L == "ا" and i > 0 and A[i - 1] == "و":
            opts.append(("", j))
        for mark, nj in opts:
            if isinstance(nj, tuple):  # lång vokal: nästa bokstav tar vokalen
                k = nj[1]
                r = go(i + 2, k + 1)
                if r is not None:
                    return L + mark + A[i + 1] + r
                continue
            r = go(i + 1, nj)
            if r is not None:
                return L + mark + r
        return None

    return go(0, 0)


def keep_final_vowel(ar):
    """Rösten läser sista ordet i pausform och tappar sista korta vokalen (فَعَلْتُ blir faʿalt).
    En lång vokalbokstav efter vokaltecknet gör att vokalen hörs (faʿaltu).
    Samma sak med -un och -in (أَهالٍ blir ahāl): där skrivs n:et ut.
    Varje "m. / f."-form för sig, och ? eller ! sist räknas inte (حالُكَ؟ / حالُكِ؟)."""
    def one(p):
        m = re.match(r"(.*?)([\s؟،!?.]*)$", p.strip(), re.S)
        s, tail = m.group(1), m.group(2)
        if s[-1:] in ("ٌ", "ٍ"):
            return s[:-1] + {"ٌ": DAMMA, "ٍ": KASRA}[s[-1]] + "ن" + tail
        end = {FATHA: "ا", DAMMA: "و", KASRA: "ي"}.get(s[-1:])
        return s + (end or "") + tail
    return " / ".join(one(p) for p in ar.split("/")) if "/" in ar else one(ar)


def flags(text):
    """Texten och valen efter | (långsam, sista, mening, utan-slutvokal, ipa=...)."""
    text, *f = text.split("|")
    return text, set(f)


def last_word(wav):
    """Behåller bara det sista som sägs: allt efter sista pausen i ljudet (wav, 16 bitar mono).
    Tystnaden efter ordet kortas till 100 ms. Gränsen för tyst är låg, annars klipps
    sista konsonantens släpp bort (ṭ i ghalaṭ kommer svagt, en bit efter vokalen)."""
    with wave.open(io.BytesIO(wav)) as w:
        params, pcm = w.getparams(), array.array("h", w.readframes(w.getnframes()))
    step = params.framerate // 100  # 10 ms
    loud = [max(map(abs, pcm[i:i + step]), default=0) for i in range(0, len(pcm), step)]
    limit = max(loud) * 0.01
    # Sista tystnaden på minst 150 ms före slutet av talet.
    end = max(i for i, v in enumerate(loud) if v > limit)
    start, quiet = 0, 0
    for i in range(end, -1, -1):
        quiet = quiet + 1 if loud[i] <= limit else 0
        if quiet >= 15:
            start = i + quiet - 12  # 120 ms före ordet, så att svaga början som gh kommer med
            break
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        w.writeframes(pcm[start * step:(end + 10) * step].tobytes())
    return out.getvalue()


CARRIER = "اَلْبَيْتُ"


def after_carrier(wav):
    """Tar bort "al-baytu" före ordet: klipper i första korta glappet (minst 30 ms under 5 %)
    efter att talet börjat. Glappet efter -tu finns alltid, men ordet självt kan ha tysta
    ställen vid t, b och k, så sista glappet går inte att använda."""
    with wave.open(io.BytesIO(wav)) as w:
        params, pcm = w.getparams(), array.array("h", w.readframes(w.getnframes()))
    step = params.framerate // 100  # 10 ms
    loud = [max(map(abs, pcm[i:i + step]), default=0) for i in range(0, len(pcm), step)]
    top = max(loud)
    end = max(i for i, v in enumerate(loud) if v > top * 0.01)
    onset = next(i for i, v in enumerate(loud) if v > top * 0.2)
    start, quiet = 0, 0
    for i in range(onset, end):
        quiet = quiet + 1 if loud[i] <= top * 0.05 else 0
        if quiet >= 3:
            # Ordet börjar där ljudet åter går över 5 %. 30 ms före det, annars hörs slutet
            # av al-baytu som ett "to" före ordet (to-maṭbakh).
            word = next(j for j in range(i, end) if loud[j] > top * 0.05)
            start = max(word - 3, 0)
            break
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        w.writeframes(pcm[start * step:(end + 10) * step].tobytes())
    return out.getvalue()


def cut_vowel(wav, keep=3):
    """Klipper bort slutvokalen men behåller släppet av konsonanten före: tarakt fick inget
    hörbart t, men rösten säger taraktu, och 30 ms efter t-smällen tonas ljudet ut."""
    with wave.open(io.BytesIO(wav)) as w:
        params, pcm = w.getparams(), array.array("h", w.readframes(w.getnframes()))
    step = params.framerate // 100  # 10 ms
    loud = [max(map(abs, pcm[i:i + step]), default=0) for i in range(0, len(pcm), step)]
    top = max(loud)
    # Sista tystnaden (konsonantens stängning) före slutvokalen, sedan släppet efter den.
    end = max(i for i, v in enumerate(loud) if v > top * 0.2)
    gap = max(i for i in range(end) if loud[i] < top * 0.05)
    release = next(i for i in range(gap, len(loud)) if loud[i] > top * 0.05)
    seg = pcm[:(release + keep) * step]
    fade = 2 * step  # 20 ms uttoning
    for j in range(fade):
        seg[-fade + j] = int(seg[-fade + j] * (1 - j / fade))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        w.writeframes(seg.tobytes())
    return out.getvalue()


TA_END = re.compile(r"(.)([ً-ْ]*)ة[ً-ْ]*(?=[\s؟،!?.]*$)")


def final_ta(text):
    """ة sist i ordet läses -a, men rösten tappar det ofta (كُرّاسة blev kurrās).
    Med ه och sukun i stället hörs -a. Varje "m. / f."-form för sig."""
    def fix(m):
        # Efter ا (فَتاة, fatāh) behövs ingen fatha.
        marks = m.group(2) if FATHA in m.group(2) or m.group(1) == "ا" else m.group(2) + FATHA
        return m.group(1) + marks + "ه" + SUKUN
    return " / ".join(TA_END.sub(fix, p.strip()) for p in text.split("/"))


def synth(key, region, lang, voice, text, wav=False):
    text, f = flags(text)
    slow = "långsam" in f
    # "m. / f."-former läses som två ord med en kort paus emellan.
    parts = [p.strip() for p in text.split("/")]
    ipa = next((x[4:] for x in f if x.startswith("ipa=")), None)
    # IPA kan också delas med "/", en per form: "كيفك؟ / كيفك؟|ipa=kiːfak / kiːfik".
    ipas = [p.strip() for p in ipa.split("/")] if ipa else []
    if len(ipas) == len(parts):
        parts = [f'<phoneme alphabet="ipa" ph="{escape(i)}">{escape(p)}</phoneme>' for p, i in zip(parts, ipas)]
        spoken = " ، ".join(parts)
    else:
        spoken = escape(" ، ".join(parts))
        if ipa:
            spoken = f'<phoneme alphabet="ipa" ph="{escape(ipa)}">{spoken}</phoneme>'
    ssml = (f'<speak version="1.0" xml:lang="{lang}"><voice name="{voice}">'
            f'<prosody rate="{"-35%" if slow else "-10%"}">{spoken}</prosody></voice></speak>')
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm" if wav else "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "arabiska-ordkort",
        })
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:  # för många anrop, vänta och försök igen
                time.sleep(15 * (attempt + 1)); continue
            if e.code in (401, 403):
                sys.exit("Azure godtog inte nyckeln eller regionen. Kontrollera KEY 1 och Plats/region.")
            raise
        except urllib.error.URLError:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("Fick inget svar från Azure efter flera försök.")


def save(index, index_path):
    json.dump(index, open(index_path, "w", encoding="utf-8"), ensure_ascii=False)
    # Samma lista som skript, så att appen hittar ljudet även när index.html öppnas direkt från disken.
    with open(os.path.join(OUT, "index.js"), "w", encoding="utf-8") as f:
        f.write("window.LJUD = " + json.dumps(index, ensure_ascii=False) + ";\n")


def main():
    male = "--man" in sys.argv
    key = os.environ.get("AZURE_SPEECH_KEY") or getpass.getpass("Nyckel (KEY 1, syns inte när du skriver): ").strip()
    region = os.environ.get("AZURE_SPEECH_REGION") or input("Region (till exempel westeurope): ").strip()
    words = json.load(open(os.path.join(HERE, "ord.json"), encoding="utf-8"))

    # Samma arabiska text i samma dialekt behöver bara en fil.
    todo = {}
    for w in words:
        for d in ("leb", "irq", "msa"):
            for ar, tr in (w.get(d) or {}).get("f", []):
                if ar.strip():
                    todo.setdefault(f"{d}|{ar}", (d, ar, tr))

    os.makedirs(OUT, exist_ok=True)
    index_path = os.path.join(OUT, "index.json")
    index = json.load(open(index_path, encoding="utf-8")) if os.path.exists(index_path) else {}
    spoken_path = os.path.join(OUT, "uttal.json")
    spoken = json.load(open(spoken_path, encoding="utf-8")) if os.path.exists(spoken_path) else {}
    def say(k):
        d, ar, tr = todo[k]
        if k in UTTAL:
            return UTTAL[k]
        if d == "msa":
            return final_ta(keep_final_vowel(ar))
        return (d in ("leb", "irq") and tr and vocalize(ar, tr, d)) or ar
    left = [k for k in todo if not (k in index and os.path.exists(os.path.join(OUT, index[k])))
            or spoken.get(k, todo[k][1]) != say(k)]
    print(f"{len(todo)} uppläsningar totalt, {len(left)} kvar att skapa.")

    for n, k in enumerate(left, 1):
        d, ar, _ = todo[k]
        lang, voice = VOICES[male][d]
        # Bara sista ordet: klipps ur wav, eftersom det inte finns något här som kan klippa mp3.
        opts = flags(say(k))[1]
        last = "sista" in opts or "mening" in opts or "utan-slutvokal" in opts
        name = f"{d}/{hashlib.sha1(ar.encode('utf-8')).hexdigest()[:12]}.{'wav' if last else 'mp3'}"
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
        audio = synth(key, region, lang, voice, (CARRIER + " " if "mening" in opts else "") + say(k), wav=last)
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(after_carrier(audio) if "mening" in opts else cut_vowel(audio) if "utan-slutvokal" in opts
                    else last_word(audio) if last else audio)
        index[k] = name
        spoken[k] = say(k)
        json.dump(spoken, open(spoken_path, "w", encoding="utf-8"), ensure_ascii=False)
        if n % 10 == 0 or n == len(left):
            save(index, index_path)
            print(f"  {n}/{len(left)} klara")
        time.sleep(PAUSE)

    save(index, index_path)
    print("Klart. Lägg upp mappen ljud/ bredvid index.html på GitHub.")


if __name__ == "__main__":
    main()
