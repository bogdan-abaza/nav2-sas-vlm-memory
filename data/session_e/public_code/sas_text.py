"""
sas_text.py — modul unic de normalizare, tokenizare si detectie a negatiei.

Introdus in v4.8-review pentru a elimina divergenta dintre tokenizatorul din
vlm_navigator_node (potrivire) si cel din memory_extractor (invatare).
Ambele componente importa DE AICI. Nu mai exista liste locale de stopwords.

Referinte review ROBOT-D-26-01090: R1 #8, R2 #1, AC-6.

v1.1.0 fata de v1.0.0:
  - alias-urile RO sunt aplicate IN tokenize() si cluster_key(), nu doar
    disponibile ca functie separata (R2 #1)
  - normalize() transforma '_' in spatiu, deci "lab_cb204" -> "lab cb204"
  - markeri de negatie suplimentari (forme contrase si RO)
"""
import re
import unicodedata

SAS_TEXT_VERSION = "1.2.0"

# ── Markeri de negatie: NICIODATA stopwords. Prezenta oricaruia blocheaza
#    potrivirea determinista si forteaza escaladarea. ─────────────────────
NEGATION_MARKERS = frozenset({
    # engleza
    'not', 'no', 'never', 'none', 'nor', 'neither', 'without',
    'avoid', 'except', 'exclude', 'excluding', 'dont', 'doesnt', 'didnt',
    'cannot', 'cant', 'wont', 'shouldnt', 'wouldnt', 'mustnt',
    # v1.1.0: forme contrase si cuantificatori negativi
    'isnt', 'arent', 'wasnt', 'werent', 'havent', 'hasnt', 'hadnt',
    'nothing', 'nobody', 'nowhere', 'instead',
    # romana (fara diacritice, textul e normalizat NFKD inainte)
    'nu', 'fara', 'niciodata', 'nici', 'nicaieri', 'exceptand', 'evita',
    # v1.1.0: romana
    'deloc', 'nicidecum', 'interzis',
})

# ── v1.2.0: negatia purtata de EXPRESII, nu de particule. ────────────────
#    "go anywhere but cb204" si "du-ma altundeva decat la toaleta" nu contin
#    niciun marker de mai sus. Treceau prin poarta si se rezolvau determinist
#    -- in cazul lui `but cb204`, chiar la nodul INTERZIS. Vezi antetul
#    patch-ului: 7 din 17 formulari ale taxonomiei E2 treceau nedetectate.
#
#    `but` nu se adauga ca marker izolat -- "go to cb204 but slowly" e
#    afirmativ. Se adauga expresiile, care nu au ambiguitate.
NEGATION_PHRASES = (
    # engleza
    'other than', 'anything but', 'anywhere but', 'somewhere but',
    'somewhere else', 'anywhere else', 'some other', 'any other',
    # romana (text normalizat NFKD, fara diacritice)
    'in alta parte', 'in alt loc', 'altundeva decat', 'altceva decat',
    'alta parte decat', 'in afara de', 'in afara lui',
)

# Cuvinte care singure exprima o alternativa explicita. Spre deosebire de
# markerii slabi din negation_guard ('somewhere', 'oriunde'), acestea nu apar
# in instructiuni afirmative: "du-ma altundeva" e prin definitie o excludere.
#
# Riscul e asimetric si de aceea multimea e inclusiva: un fals pozitiv aici
# inseamna escaladare la L3b cu notificare de negatie -- conservator, robotul
# nu pleaca gresit. Un fals negativ inseamna navigare la un nod interzis.
EXCLUSION_STRONG = frozenset({
    'except', 'excepting', 'besides', 'instead', 'alternative',
    'altundeva', 'altceva', 'exceptand', 'elsewhere',
})

# ── Lista unificata de stopwords = reuniunea celor doua liste istorice
#    (_M3_STOPWORDS din navigator, 101 intrari + _STOPWORDS din extractor,
#    60 intrari; reuniune 118), din care s-au scos markerii de negatie
#    'no' si 'not'. Rezultat: 116. ────────────────────────────────────────
STOPWORDS = frozenset({
    # engleza — articole, prepozitii, auxiliare
    'a', 'an', 'the', 'to', 'at', 'in', 'on', 'of', 'for', 'with', 'by', 'from', 'as',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'am',
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it', 'its', 'they',
    'this', 'that', 'these', 'those',
    'can', 'could', 'would', 'should', 'will', 'shall', 'may', 'might', 'must',
    'do', 'does', 'did', 'have', 'has', 'had',
    'and', 'or', 'but', 'so', 'if', 'then', 'than',
    'please', 'some', 'any', 'something', 'someone',
    'where', 'what', 'which', 'who', 'when', 'how',
    'go', 'goto',
    # romana
    'la', 'de', 'pe', 'cu', 'si', 'sa', 'sau', 'un', 'o', 'ul',
    'este', 'sunt', 'era', 'fi', 'fie',
    'eu', 'tu', 'el', 'ea', 'noi', 'voi', 'ei', 'ele',
    'te', 'se', 'ne', 've', 'ma', 'mi', 'ti',
    'ca', 'din', 'pentru', 'spre', 'catre', 'prin', 'peste',
    'rog', 'poti', 'putea', 'trebuie', 'mergi', 'du', 'duca',
}) - NEGATION_MARKERS

MIN_TOKEN_LEN = 2

# ── Alias-uri RO -> clasa POI (engleza), pentru instructiuni bilingve.
#    Raspunde la R2 #1: pipeline-ul bilingv nu avea corespondenta de
#    vocabular, doar stopwords romanesti. ─────────────────────────────────
RO_CLASS_ALIASES = {
    'toaleta': 'restroom', 'toalete': 'restroom', 'baie': 'restroom',
    'wc': 'restroom', 'veceu': 'restroom',
    'planta': 'potted plant', 'plante': 'potted plant',
    'floare': 'potted plant', 'flori': 'potted plant', 'ghiveci': 'potted plant',
    'calorifer': 'radiator', 'radiator': 'radiator',
    'laborator': 'laboratory', 'laboratoare': 'laboratory',
    'stingator': 'fire extinguisher', 'extinctor': 'fire extinguisher',
    'scaun': 'chair', 'fotoliu': 'chair',
    'fereastra': 'window', 'geam': 'window',
    'coridor': 'corridor', 'hol': 'corridor',
}


def normalize(text: str) -> str:
    """Lowercase, elimina diacriticele (NFKD), '_' -> spatiu, colapseaza spatiile."""
    text = (text or '').lower().strip()
    nfkd = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in nfkd if not unicodedata.combining(c))
    text = text.replace('_', ' ')
    return re.sub(r'\s+', ' ', text)


def _words(text: str):
    """Tokenii bruti, cu apostrofurile colapsate (don't -> dont)."""
    norm = normalize(text)
    norm = re.sub(r"['\u2018\u2019`]", '', norm)   # don't -> dont
    norm = re.sub(r'[^\w\s]', ' ', norm)
    return norm.split()


def expand_aliases(text: str) -> str:
    """Adauga echivalentul in engleza al termenilor romanesti recunoscuti."""
    out = []
    for w in _words(text):
        out.append(w)
        if w in RO_CLASS_ALIASES:
            out.extend(RO_CLASS_ALIASES[w].split())
    return ' '.join(out)


def tokenize(text: str) -> set:
    """
    Multimea de tokeni de continut. Identica la invatare si la potrivire.
    v1.1.0: aplica alias-urile RO inainte de filtrare, deci
    'du-ma la toaleta' si 'take me to the restroom' impart tokenul 'restroom'.
    """
    words = _words(text)
    expanded = []
    for w in words:
        expanded.append(w)
        if w in RO_CLASS_ALIASES:
            expanded.extend(RO_CLASS_ALIASES[w].split())
    return {t for t in expanded
            if len(t) >= MIN_TOKEN_LEN and t not in STOPWORDS}


def detect_negation(text: str):
    """
    Returneaza (are_negatie: bool, markeri_gasiti: list).
    Se aplica pe tokenii bruti, INAINTE de filtrarea stopwords.

    Trei clase de semnal, toate obligatorii:
      MARKERI   negatia purtata de o particula   -- not, nu, never, except
      EXPRESII  negatia purtata de o prepozitie sau un comparativ
                -- "anywhere but", "other than", "altundeva decat",
                   "in afara de". Acestea NU contin niciun marker de cuvant,
                   deci fara ele poarta le lasa sa treaca.
      ALTERNATIVE  cuvinte care singure cer explicit altceva -- altundeva,
                elsewhere. "du-ma altundeva" nu are nici marker, nici expresie.
    """
    found = [w for w in _words(text) if w in NEGATION_MARKERS]

    norm = normalize(text)
    found += [ph for ph in NEGATION_PHRASES if ph in norm]

    words = set(_words(text))
    found += sorted((words & EXCLUSION_STRONG) - NEGATION_MARKERS)

    return (len(found) > 0, found)


def jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def cluster_key(text: str) -> frozenset:
    """
    Cheia canonica de grupare M3 la invatare.
    Instructiunile negate NU se grupeaza cu cele afirmative: markerii de
    negatie raman in cheie (nu sunt stopwords).
    """
    toks = tokenize(text)
    return frozenset(toks) if toks else frozenset({normalize(text)})
