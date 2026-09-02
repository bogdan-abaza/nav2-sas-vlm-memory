# E7 — set de instrucțiuni, sigilat

**Data sigilării:** 20 august 2026, înainte de prima misiune E7 din ziua 2.

| Fișier | Rol | `md5` |
|---|---|---|
| `E7_set_sigilat.csv` | **v1**, forma minimală — angajamentul pe cuvintele de conținut | `7986ddb5bca58f45956f45d8086993e1` |
| `E7_set_sigilat_v2.csv` | **v2**, forma naturală — setul care se rulează fizic | `1ebb16730b30a1ee8c97f11e6b6f2cdd` |

**28 de instrucțiuni în fiecare versiune.** Orice modificare schimbă `md5` și e detectabilă.

---

## Ce revendicăm — și ce nu

**Nu** revendicăm „independently generated". Revendicăm:

> Grilă declarată înainte de a scrie propozițiile · o singură formulare per celulă · fără rescriere după ce s-au văzut rezultate · sigilată cu `md5` înainte de prima misiune · toate cele 28 se rulează, fără excepție.

Adică **pre-înregistrare**, nu independență. Afirmație mai slabă decât cea cerută de R1 #4, dar verificabilă.

Independența se completează separat, după sesiune, fără să atingă datele:
1. un coleg citește cele 28 și marchează câte sună a manual de robot;
2. un set mic, colectat efectiv de la persoane de pe hol, raportat ca experiment suplimentar.

## De ce două versiuni

**v1** conține doar cuvintele de conținut, în formă telegrafică („water", „tired", „chair"). A fost sigilat **întâi**. **v2** se obține prin *expandare*: se adaugă limbaj de purtare — verb, pronume, articol — fără a schimba conținutul.

Ordinea contează: v1 fiind sigilat înainte, nimeni nu poate susține că alegerea cuvintelor de conținut a fost făcută după ce s-a văzut ceva. Expandarea nu mai poate schimba ținta, doar naturalețea.

Verificare automată v1 → v2, cu `sas_text.tokenize` din codul înghețat `f973aa0`: **27 din 28 de celule păstrează integral tokenii de conținut din v1.**

Singura excepție declarată: `S-P3`, unde `resting` a devenit `rest` la corectarea gramaticală. Niciunul dintre cei doi tokeni nu apare în ontologie sau în tabelul de alias, deci schimbarea nu are efect asupra rezolvării.

**Corectură ortografică aplicată la v2**, strict la nivel de scriere, fără substituție de cuvinte: `attent→attend`, `char→chair`, `windows→window`, `plat→plant`, `relx→relax`, `wjere→where`, `Wher→Where`, `I'ma→I'm`. Trei dintre ele erau critice — `char`, `windows` și `plat` anulau exact potrivirea pe care celula trebuia s-o testeze, fiindcă `tokenize` nu face lematizare.

Cuvânt de conținut adăugat față de v1: **`class`** în `G-1`. Nu e termen din ontologie, nu schimbă ținta. Se consemnează.

## Proveniență, per celulă

| Statut | Celule | Ce înseamnă |
|---|---|---|
| **RO-first-blind** | 15 | scrise întâi în română, **înainte** ca autorul să fi văzut vreun termen din ontologie |
| **EN-direct** | 13 | scrise direct în engleză, **după** ce în conversația de proiectare fuseseră pomeniți termeni din ontologie |

Setul fizic se rulează **în engleză, v2**. Versiunile **v1 minimal** și **română** se rulează **offline**, prin rezolverul înghețat — trei condiții pe aceleași 28 de intenții, la costul de teren al uneia.

## Grila

Șase categorii de destinație × patru niveluri de precizie = 24, plus 4 celule de graniță.

| Nivel | Ce face vorbitorul | Ce trebuie să facă ascultătorul |
|---|---|---|
| P1 | numește locul prin numele lui | recunoaște un nume |
| P2 | numește un obiect din el sau o proprietate | leagă obiect/atribut de loc |
| P3 | spune de ce are nevoie | deduce locul din nevoie |
| P4 | descrie o stare | deduce nevoia, apoi locul |

**Regulă de interpretare:** categoria e dispozitivul de elicitare; **cheia urmează sensul**. Patru celule au un referent natural diferit de categoria sub care au fost cerute (`W-P2`, `W-P4`, `P-P3`, parțial `T-P2`). Se consemnează ambele, nu se forțează formularea.

## Cheia

- `acceptabil` — noduri considerate răspuns corect
- `incorect` — noduri considerate greșeală explicită
- `-1` — abținerea sau cererea de clarificare este răspunsul corect

Două celule au `acceptabil = -1`: `H-P2` (fără referent) și `G-3` (țintă nemapată).

## Ce atinge determinist ontologia, în v2

| Celulă | Token | Noduri atinse |
|---|---|---|
| `L-P1`, `G-2` | `cb203` | 22, 23 |
| `L-P3`, `G-1`, `G-2` | `lab` | 5, 8, **15**, 22, 23 |
| `T-P1` | `men`, `toilet` | 0 · 0, 4 |
| `S-P1`, `G-4` | `chair` | 15 |
| `W-P1` | `window` | 14, 20 |
| `W-P2` | `plant` | 13, 14, 15, 19, 20, 21 |
| `H-P1` | `hall`, `exit` | 1, 2 · 1, 2, 23 |

**Observație de raportat:** tokenul `lab` se potrivește și cu `lab_chair`, deci trimite la nodul **15**, care este un *scaun*, nu un laborator. E o ambiguitate reală, produsă de denumirea `obj_id`-urilor, și afectează `L-P3`, `L-P4` și `G-1`.

## Suprapunerea lexicală — calculată ÎNAINTE de rulare

Cu `sas_text.tokenize` / `jaccard` din codul înghețat, față de cele șase exemplare stocate în digestul `97241265…`:

| Bandă | Celule (v2) |
|---|---|
| `J = 0` | 21 |
| `0 < J < 0.50` | 7 — maxim `W-P3` = **0.375** |
| `0.50 ≤ J < 0.75` | 0 |
| `J ≥ 0.75` — declanșează M3 | **0** |

**Nicio instrucțiune nu poate declanșa pasul 0 al cascadei.** Calculat înainte de prima misiune.

## Predicții declarate înainte de rulare

**1. Memoria M3 potrivește formularea, nu sensul.**
`W-P3` („fresh air") și `W-P4` („relax") coincid **ca intenție** cu două preferințe stocate — promovate de 19, respectiv 8 ori. Ies la `J = 0.375` și `0.200`, sub pragul de 0.75. Predicția: **pasul 0 nu se declanșează, deși intenția e memorată.** Relevant pentru R1 #5 și R2.

**2. Stratul de alias românesc acoperă obiecte, nu nevoi.**
`sas_text.py` conține `RO_CLASS_ALIASES`, 22 de intrări, aplicate în `tokenize`: `toaleta→restroom`, `scaun→chair`, `floare→potted plant`, `laborator→laboratory`, `fereastra/geam→window`, `calorifer/radiator→radiator`, `stingator/extinctor→fire extinguisher`, `hol/coridor→corridor`.

Deci intrarea în română **poate** ajunge la cascada deterministă — dar numai pentru substantive de loc și de obiect. Niciun cuvânt de nevoie sau de stare nu are echivalent: „apă", „odihnesc", „obosit", „așteptare" rămân neacoperite.

Predicția: în brațul românesc, degradarea apare la **P3 și P4**, nu uniform. Brațul măsoară **acoperirea stratului de alias**, nu absența lui.

*(Notă de corectitudine: o versiune anterioară a acestui protocol afirma că întreaga cascadă e indisponibilă pentru română. Afirmația era greșită — tabelul de alias nu fusese verificat — și a fost retrasă înainte de rulare.)*

**3. Forma minimală vs forma naturală.**
Brațul v1 („water", „tired") conține aceiași tokeni de conținut ca v2, dar fără limbaj de purtare. Predicția: rezoluția deterministă e **identică** pe v1 și v2, fiindcă tokenii de conținut coincid; diferențele care apar provin din L3b, care primește textul întreg.

**4. Stratul dinamic YOLO poate deturna două celule.**
`L-P2` („computer") — nu există obiect static `computer`; clasa YOLO `laptop` apare pe 14 noduri, **inclusiv nodul 4 (toaleta femei)**.
`T-P2` („water") — chiuvetele sunt detecții YOLO la nodul 0 **și nodul 5 (cb204)**.
Pentru ambele se consemnează **numărul de obiecte brute din magazia dinamică la momentul rulării**. Fără el, rezultatul nu e interpretabil.

**5. `G-3` are o capcană lexicală.**
Nu există obiect static `fire_hydrant_cb202` în ontologia servită. Există însă clasa YOLO `stop sign` la nodurile 0, 22, 23, și două artefacte `fire hydrant` la 13 și 16. Răspunsul corect e **abținerea**; oricare dintre acele noduri e greșeală.

## Cum se raportează

**Niciodată ca o singură cifră.** Rata se dă **stratificat pe nivel de precizie** P1→P4. O rată agregată dintr-un set stratificat ar repeta exact greșeala atacată de R1 la cei 88%.

Setul **nu** este un eșantion naturalist. Distribuția naturală a cererilor într-un hol universitar e dominată de referință explicită — de aceea rata inițială era mare. Grila supra-eșantionează deliberat capătul greu. Se declară explicit în text.

Dacă rata **nu** scade monoton P1→P4, e un rezultat, nu o eroare.

## Limitări cunoscute ale setului, declarate

- `S-P2`, `S-P3`, `S-P4` duc toate la `{9, 15}` și au toate `J = 0`: categoria «loc de stat» are o singură celulă discriminantă, `S-P1`.
- `L-P3` și `L-P4` țintesc aceeași mulțime; distincția lor e lexicală (`lab` vs `class`), nu de destinație.
- `P-P2` și `P-P4` conțin amândouă `green`; varietatea internă a categoriei «plantă» e mică.
- `W-P3` și `P-P3` exprimă aceeași intenție („aer curat") prin formulări diferite. Nu e duplicat de text, ci pereche utilă pentru predicția 1.
- `G-4` nu este o ambiguitate: există un singur scaun static, iar scaunele YOLO sunt suprimate de filtru. Testează calea de proximitate.
- Varianta „stairs", propusă inițial pentru `H-P2`, a fost înlocuită cu „other location". Se pierde o a doua țintă nemapată; rămâne una, `G-3`.

## Constrângere de ordine

`W-P3` corespunde ca intenție unei preferințe promovate care ar putea fi reîntărită de E4.
**E7 rulează înaintea lui E4**, sub digestul publicat înghețat, ca E1–E3.

> Ziua 2: **E3 → E7 → E6 → E4 → E5**

Înainte de prima misiune E4 se verifică `md5 = 97241265…` și `content_md5 = bdc89fcf…`, pentru că E6 rulează pe digest gol și starea trebuie restaurată.

De verificat înainte de E4: niciuna dintre cele 28 nu coincide cu formulările `P1`/`P2` alese pentru E4.

---

# AMENDAMENT 1 — 20 august 2026, înainte de prima misiune E7

Consemnat **înainte** ca vreo misiune E7 să ruleze. Predicțiile de mai sus **nu au fost editate**;
corecțiile se adaugă aici, cu motivul, ca istoricul să rămână verificabil.

## A1.1 — Retragerea predicției 3

Predicția 3 afirma că, pentru intrări în română, cascada deterministă este **structural
indisponibilă**, fiindcă ontologia e integral în engleză.

**Este falsă.** `sas_text.py` conține `RO_CLASS_ALIASES`, **22 de intrări**, aplicate **în interiorul
lui `tokenize`**, deci înainte de orice potrivire:

```
toaleta, toalete, baie, wc, veceu     -> restroom
planta, plante, floare, flori, ghiveci -> potted plant
scaun, fotoliu                        -> chair
fereastra, geam                       -> window
laborator, laboratoare                -> laboratory
calorifer, radiator                   -> radiator
stingator, extinctor                  -> fire extinguisher
coridor, hol                          -> corridor
```

`scaun` **se potrivește** cu `lab_chair`, `toaleta` cu `restroom`, `floare` cu `potted plant`.
Afirmația a fost făcută fără verificarea codului și se retrage integral.

## A1.2 — Reformularea predicției 2

Predicția 2 afirma că memoria M3 e legată de limbă, pentru că exemplarele stocate sunt în engleză.
Concluzia se menține, dar **mecanismul invocat era greșit**.

Brațul românesc dă `J = 0` față de cele șase exemplare stocate **nu** fiindcă alias-urile lipsesc,
ci fiindcă **niciunul dintre cele șase exemplare nu conține un substantiv de clasă** — nu apar
`chair`, `plant`, `restroom`, `window`, `radiator`, `laboratory`. Alias-urile există, dar nu au pe ce
să se prindă.

**Predicție corectată, mai îngustă și testabilă:** stratul de alias acoperă substantive de **loc** și
de **obiect**, dar **niciun** cuvânt de nevoie sau de stare — nu există alias pentru „apă",
„odihnesc", „obosit", „așteptare". Deci, în brațul românesc, degradarea ar trebui să apară la
nivelurile **P3 și P4**, nu uniform pe toate cele patru.

## A1.3 — Corectarea suprapunerii lexicale raportate

Valorile din secțiunea „Suprapunerea lexicală" au fost calculate cu `sas_text.jaccard` aplicat
exemplar cu exemplar. Funcția care decide efectiv pasul 0 este `sas_l3a.match_m3_preference`, care
**agregă pe nod** și ia cel mai bun exemplar per nod, apoi aplică pragul `0.75` și marja de
abținere `0.10`.

Recalculat cu funcția reală de decizie, față de digestul înghețat `97241265…`:

| Celulă | `J_top` | Verdict |
|---|---|---|
| `W-P3` | **0.375** | `below_threshold` |
| `W-P4` | 0.200 | `below_threshold` |
| `W-P1` | 0.200 | `below_threshold` |
| `S-P1` | 0.167 | `below_threshold` |
| `P-P2` | 0.167 | `below_threshold` |

**Maximul este 0.375, nu 0.250** cum scria mai sus. Afirmația de fond **se menține neschimbată**:
`0 din 28` de celule declanșează pasul 0.

## A1.4 — Cum se calculează J, de aici înainte

`J` se calculează cu `sas_text.tokenize` și `sas_text.jaccard` din `f973aa0` — aceleași funcții pe
care `sas_l3a.py` le importă la liniile 21–22 pentru pasul 0. Numărarea pe cuvinte brute dă alte
valori, fiindcă `tokenize` elimină stopwords (`me`, `a`, `to`) și aplică alias-urile RO.

Exemplu: *„find me somewhere quiet"* față de *„find me a quiet corner to read"* dă **0.400** prin
funcția sistemului (2 tokeni comuni din 5) și **0.375** prin numărare naivă pe cuvinte (3 din 8).
**Numărul care se raportează este cel al codului.**
