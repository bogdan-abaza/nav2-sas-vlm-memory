# Note de rulaj, ziua 2, 21 august 2026

Ce nu se vede din audituri si nu se reconstituie mai tarziu.
Campurile marcate `<...>` se completeaza de mana inainte de livrare.

## Identitate

| Camp | Valoare |
|---|---|
| `git_commit` | `f973aa0`, arbore curat, verificat la poarta de dimineata |
| `geojson_md5` (v2 activ) | `2e48375071c0e4ea7cd38c0e48ef97c5` |
| md5 fisier digest publicat | `97241265217eb4b08e26fb718eb21f40` |
| `content_md5` digest publicat, in audit | `0fd61f9e82e8fe6991f0311014384e0c` |
| `route_graph` md5 pe disc, statie si C | `440522bc9f0c32997698310f680bfb89` |
| `route_graph_md5` servit de context | `b5736e070dfd9ced98f821c1e34255c8` |
| `route_graph_md5` calculat de navigator | `e0130b78b00ec55822dbc39a41429817` |
| `protocol_version` / `audit_schema` | `E-2026-09` / 2.2 |
| ollama / model / cuantizare | `0.30.2` / `0c8faadc50c205b8` / `Q4_K_M` |
| driver GPU / `sas_text_version` | `580.173.02` / `1.2.0` |
| `MERGE_DISTANCE_M` / `YOLO_DEDUP_RADIUS_M` / `YOLO_MIN_OBSERVATIONS` | 1.0 / 1.5 / 3 |

Serverul ollama a pornit la **09:45** si **nu a fost repornit** in cursul zilei. `vlm_model_digest`,
cuantizarea si versiunea sunt identice la prima si la ultima misiune. Identitatea sesiunii e intacta.

Md5-ul grafului de pe C a fost verificat separat si coincide cu cel de pe statie, deci nu exista o a
patra serializare.

## Artefacte de memorie

| Artefact | md5 fisier | `content_md5` | Promovari | Stare |
|---|---|---|---|---|
| digest publicat | `97241265217eb4b08e26fb718eb21f40` | `0fd61f9e82e8fe6991f0311014384e0c` | 6 | activ pana la 17:30 |
| digest GOL (E6) | `b01717118e1e479f49d931a5c96cc0c5` | `59a7c9cfa25549c9de6ec3c6e0f988d2` | 0 | folosit doar la E6 |
| digest E4.2 | `3751babfc573f36665648833ab0c98ed` | `d221ef8ad689de168b2020995693791c` | 0 | **neinstalat**, decizie coordonator |
| digest E4b | `eca5dbc8061bc3fdafdc49e12bc2c900` | `5b3f14bc71a1896da5b29a4e655479fa` | 1 (nod 9, freq 4) | **instalat 17:30**, activ la sfarsitul zilei |

Arhive: `~/arhiva/memory_digest_INGHETAT_20260821.json` si
`~/arhiva/memory_digest_inainte_E4b_1730.json`, ambele `97241265…`.
Directoarele complete `~/digest_gol/`, `~/digest_E4.2/`, `~/digest_E4b/` se aduc la livrare, cu
fisierele M1 pana la M5.

Pentru toate cele trei digesturi produse de extractor, `content_md5` scris in fisier coincide cu cel
calculat cu `sort_keys=True, separators=(',',':')`, deci navigatorul si extractorul calculeaza identic.

## Amendamente formulate azi

**A11.** `MEMORY_DIGEST_PATH` nu se lasa gol. Valoarea implicita din navigator, liniile 277 pana la
280, este `~/Documents/VLM/memory/memory_digest.json`, fisier din 17 august cu **8 promovari** si
`content_md5 = 2805d6a0`. Regula „gol inainte de E3" din fisa se retrage. Ziua 1 a rulat corect
fiindca variabila fusese exportata manual; azi s-a pierdut la terminale noi si a fost prinsa dupa
ancore, inainte de E3.

**Completare la A11, nescrisa initial.** Dupa E6 **nu** se face `unset`, cum cer fisa si mesajul din
`blocuri.env`: se reexporta pe digestul publicat. `unset` ar fi pornit E4 pe fisierul din 17 august.

**A12.** Digestul gol nu este incarcat de navigator. `load_memory_digest`, linia 619, il respinge
fiindca `top_entities` si `l3a_promotions_ready` sunt ambele vide. Verificarea prin
`digest_content_md5` din fisa se retrage si se inlocuieste cu `memory_digest_path`, `memory_status`,
`memory_loaded`, `m3_preferences_count`.

**Corectura la erata A12, de trimis coordonatorului.** Tabelele C4 si C5 afirma ca la E6 se scrie
`memory_digest_hash`. **Nu se scrie.** Masurat pe ambele misiuni de pe B: `memory_digest_hash = None`,
`memory_digest_size_bytes = 0`. Hashul fisierului se calculeaza la liniile 1083 pana la 1086, in
ramura `if self._memory_digest is not None`, la care nu se ajunge cand digestul e respins.

**A13.** Rata de esec L3b se raporteaza per apel, nu per misiune. Prag recalibrat la 35% din apelurile
L3b, fata de referinta de 20% din ziua 1.

**D1a.** Sursa pentru compilarea E4.2 se restrange la faza E4.1. `extract_m3` primeste toate deciziile
fara filtru pe metoda si grupeaza pe `cluster_key`, deci pe tokenii textului. `AB-S1` si `AB-S3o` din
E6 au text identic cu `S1` si `S3o` din E3 si le-ar fi furnizat rezolvarea `L3b_vlm` care le lipsea.

**D4.** Constanta `bdc89fcf` era o eticheta falsa in `digest_hashes.txt` din livrarea zilei 1. Nu
exista doua conventii de hash in cod. Corectat in `verifica_start.sh`, care da acum cod 0.

## Abateri de configuratie

- **Serverul de context de pe C a pornit fara `route_graph_path` si `semantic_objects_path`**, ambele
  absente, nu gresite. Setate la cald cu `ros2 param set`. Diferit de ziua 1, unde pe B erau
  hardcodate caile lui C. Ambele se pierd la fiecare repornire a nodului si au fost repuse de fiecare
  data, pe ambele platforme.
- **`verifica_start.sh` si `genereaza_digest_gol.sh` presupun un director `config/`** care contine si
  digestul, si ontologia. Pe statie digestul e in `sprint_73_delivery/memory/`, ontologia in `maps/`.
  Rezolvat cu `/tmp/cfg_gate`, doua simlinkuri, fara sa se atinga nimic din `~/Documents/VLM`.
- **`sas_navigator` nu exista in `ros2 pkg list`.** S-a ramas pe
  `python3 vlm_navigator_node_v4_8_review.py`, aceeasi forma ca in ziua 1, deci comparabilitatea intre
  zile e pastrata.
- **`blocuri.env` face `unset CONC_GROUP` la intrare**, deci la E5 variabila se exporta **dupa**
  `source`, contrar secventei din fisa.
- **`blocuri.env` nu cunoaste E4b.** `EXPERIMENT_ID` si `EXPERIMENT_PHASE` s-au exportat manual.
- **`semantic_localizer` are 2 PID-uri pe B** (launch plus nod) si **1 pe C**. `nav2_route
  route_server` apare in `grep semantic_localizer` din cauza caii catre fisierul de parametri si
  **nu se omoara**.
- **`queue_ms` nu se poate calcula.** Formula din fisa cere `response_at` si `request_sent_at`;
  niciunul nu exista in schema 2.2. `timing` contine doar `resolve_ms`, `vlm_ms`, `nav_total_s`.
- **Captura din sectiunea 3 a documentului E4b nu functioneaza ca scrisa.**
  `/tmp/vlm_debug_*.json` se suprascriu de apelul de **confirmare**, care vine dupa cel de decizie.
  Copiate dupa misiune, dau mereu confirmarea.
- **Inexactitate in fisa, la E5.** Multimea declarata pentru `potted plant` este `13, 15, 19, 20, 21`,
  dar nodul **14** este `plant_5` in ontologie, tinta lui `S3o` din E3. C a ales 14 la pair3.
  Disjunctia nu e afectata, 14 e pe traseul estic.

## Magazia dinamica YOLO

Ambele platforme au pornit ziua de la 0. Toate arhivele in `~/dyn_arhiva/` pe fiecare robot.

| Moment | B, inainte | B, dupa | C, inainte | C, dupa |
|---|---|---|---|---|
| dimineata | 24 | 0 | 20 | 0 |
| inainte de E3 pe C | | | | |
| dupa E3 | `<nemasurat, robot oprit inainte de citire>` | | 46 | |
| inainte de E7 | 52 | 0 | | |
| dupa E7 | 36 | | | |
| inainte de E6 | 36 | 0 | 46 | 0 |
| dupa E6 | 8 | | 17 | |
| inainte de E4 | 18 | 0 | 17 | 0 |
| dupa E4.0 + E4.1 | | | 35 | |
| inainte de E5 | 18 | 0 | 35 | 0 |
| la pornirea E5 | 3 | | 4 | |
| inainte de E4b | 14 | 0 | | |
| final | 13 | | 30 | |

Rata masurata pe C in E3: **46 obiecte pe 25 de misiuni, 1.84 pe misiune**, fata de 2.7 in ziua 1.
Nu e o constanta a platformei; se raporteaza cu intervalul, nu ca valoare unica.

Cifra pentru B la sfarsitul lui E3 s-a pierdut: robotul a fost oprit inainte de citire. Se recupereaza
partial din golirea de dinainte de E7, care acopera E3 plus ancorele: 52 de obiecte.

Prompturile de decizie au avut azi **5203 pana la 5990 octeti**, fata de 10.3 pana la 12.6 kB in ziua
1. Politica de golire pe blocuri functioneaza.

## Esecuri de VLM

**10 esecuri din 63 de apeluri L3b, 15.9%.** Ziua 1: 4 din 20, 20%. Pragul A13 de 35% neatins.
Niciun esec in E3, unde rezolvarea e aproape integral determinista.

| Bloc | Misiune | Ora | Eroare |
|---|---|---|---|
| E7 | `S-P2` | `<de completat>` | `Expecting property name enclosed in double quotes: line 1 column 2 (char 1)` |
| E7 | `P-P4` | `<de completat>` | `Expecting value: line 1 column 26 (char 25)` |
| E7 | `H-P3` | `<de completat>` | `Expecting value: line 3 column 11 (char 27)` |
| E4.1 | `P1` rep 2, C | 14:42 | `raspuns L3b fara JSON (done_reason=length, eval_count=500)` |
| E4.0 | `P1` rep 0, B | 15:14 | `raspuns L3b fara JSON (done_reason=length, eval_count=500)` |
| E4.0 | `P2` rep 0, B | 15:15 | `Expecting value: line 1 column 26 (char 25)` |
| E4.3 | `P1` rep 1, B | 15:49 | `Expecting value: line 1 column 26 (char 25)` |
| E4.3 | restul, B | `<de completat>` | 3 esecuri, mesaje in audit sub `vlm_error` |

Toate au `mission_id = null` si `run_id = ""`: esecul apare inainte de initializarea misiunii, deci
misiunile esuate **nu creeaza director** si promptul lor nu se pastreaza.

### Diagnostic, cauza nereprodusa offline

La 15:52, un prompt de control trivial, fara flag `think`, a consumat **1477 de tokeni**, aproape toti
in blocul de rationament, si a intors raspuns gol la `num_predict=100`. Cu buget de 2000 a raspuns
corect. Prima concluzie a fost ca plafonul de 500 din codul inghetat taie deliberarea.

Diagnosticul corect, cu `think: False` si promptul real al unei misiuni de pe **B**, a dat insa:

| Text | `eval_count` | `done_reason` | `thinking` |
|---|---|---|---|
| `take me to the place where deliveries arrive` (P1) | 69 | `stop` | 0 |
| `find me a quiet corner to read` (P2) | 36 | `stop` | 0 |
| `my gloves are wet, where can I dry them` (E4b) | 33 | `stop` | 0 |

**Cauza esecurilor nu se reproduce offline.** Nu e degradarea modelului, verificata. Nu e lungimea
deliberarii pe aceste texte, masurata acum: toate trei raspund in sub 70 de tokeni, de zece ori sub
plafon, iar `think: False` este respectat. Modul de esec este binar, nu gradual: fie modelul raspunde
scurt si corect, fie ignora flagul si intra in proza.

Ce ramane netestat este efectul contextului dinamic din promptul real la momentul esecului, care nu
s-a pastrat. **Legatura dintre ambiguitatea referentului si lungimea deliberarii nu se confirma pe
masuratoare directa**, desi corelatia din ratele de esec exista. Se raporteaza ca atare: corelatie
observata, mecanism neidentificat.

## Reluari si executii abandonate

| Misiune | Ce s-a intamplat | Decizie |
|---|---|---|
| ancora `AD`, B | cadere AMCL la 10:43, `audit_20260821_104307.jsonl`, fara linie de decizie | cauza externa, relansata ca `audit_20260821_104534.jsonl`; ambele raman in log |
| ancora `AD`, B | `audit_20260821_105438.jsonl`, a treia rulare | **verificare de diagnostic, in afara celor 112**, nu inlocuieste ancora oficiala |
| `pair1`, B | lansare esuata, `sas_navigator not found`, export lipsa | nu a produs audit, nu se consemneaza ca reluare |

Cele trei executii ale ancorei de pe B au toate `rep=1` si se disting **numai dupa numele fisierului**.

## Rezultate, ziua 2

### Ancore, E0

| | nod | `xy` | confirmare |
|---|---|---|---|
| `AD` C, dimineata | 8 | 0.02 | `True` `HIGH` |
| `AD` B, dimineata, oficiala | 8 | 0.233 | **`False` `LOW`** |
| `AD` B, diagnostic 10:54 | 8 | 0.14 | `True` `HIGH` |
| `AS` B, seara, oficiala | 8 | 0.226 | **`False` `LOW`** |
| `AS` C, seara | 8 | 0.182 | `True` `HIGH` |

**Cauza esecurilor de pe B, stabilita vizual si textual:** extinctorul nu se afla in campul vizual la
sosire. `finish.jpg` de la `170007` nu il contine, iar `scene_context` din raspunsul de confirmare
spune explicit ca nu e vizibil niciun extinctor. La diagnosticul reusit se vede si la start, si la
finish. Scena era neschimbata.

**Distanta nu explica esecul.** Pe cele 28 de sosiri la nodul 8 din ambele zile, B a confirmat `HIGH`
la `xy = 0.308` in ziua 1 si la 0.253 azi. Singurele alte neconfirmari sunt cele patru `E1bA` de ieri,
unde obiectul lipsea fizic. Legatura cu caderea AMCL **se retrage**: seara nu a existat cadere.

Nu e esec al stratului de confirmare. Confirmarea a raspuns adevarat despre ce vedea. Impreuna cu
`E1bA` din ziua 1, rezulta ca **sistemul confirma pe obiect vizibil**, nu pe eticheta si nu pe pozitia
din graf.

### E3, rezolutie semantica

**49 de executii din 50, 56 de linii de decizie.** Digest `0fd61f9e` cu 6 preferinte pe toate.

- **Zero confuzii de nod.** Nicio executie nu a ajuns la alt nod decat cel asteptat.
- **Doua neconfirmari**, ambele `MEDIUM`: `S6` rep 2 pe B, nodul 15, `xy = 0.423`, cea mai mare eroare
  de pozitie din bloc; `S5` rep 1 pe C, nodul 19, `xy = 0.161`, unde pozitia e buna.
- **Nodul 19 se repeta.** Ieri `SW19` a dat `False` `MEDIUM` la `xy = 0.167`, cu `expected_cue_text`
  continand un singur obiect desi nodul are doua in ontologie. Nu mai e incident izolat.
- **`missed` este stare intermediara, nu esec.** Cele 7 linii `missed` apartin executiilor cu cicluri
  multiple: `S1` rep 1 pe B, 2 cicluri; `S3` rep 1 pe B, 2 cicluri; `S5` rep 1 pe B, 6 cicluri, cu `xy`
  scazand monoton de la 4.44 la 0.172. Toate se inchid `mission_complete` la nodul corect.
- **`S1` rep 5 pe B nu s-a rulat.** H3.5 se raporteaza la 9 sosiri la nodul 0, nu 10.

### E7, set sigilat, 28 de celule pe B

`md5 = 1ebb16730b30a1ee8c97f11e6b6f2cdd` **identic inainte si dupa bloc**. Dovada de pre-inregistrare
completa.

25 de celule cu decizie, 3 esecuri VLM. Din cele 25: **17 acceptabil, 1 incorect, 7 alt nod.**
Rata se raporteaza **stratificat pe P1 pana la P4**, nu ca o cifra unica.

- **`G-3` a plecat la nodul 23**, care e in lista de noduri incorecte din CSV. Este singurul `INCORECT`
  si este chiar capcana lexicala prezisa in protocolul de sigilare. Raspunsul corect era abtinerea.
- **`H-P2` a plecat la nodul 9** in loc sa se abtina.
- **Nodul 9 apare ca atractor**: `L-P4`, `T-P4`, `P-P3`, `H-P2`, `H-P4` au deviat acolo, toate fiind
  celule de nivel P3 sau P4, adica cele in care vorbitorul descrie o nevoie sau o stare.
- **Cele 3 esecuri VLM cad pe celule cu raspuns multime**: `S-P2` (2 noduri), `P-P4` (5), `H-P3` (2).
  Niciuna dintre celulele cu raspuns unic nu a esuat.
- `resolution_step` iese `None` la aproape toate.
- Obiecte brute in magazie in timpul blocului: 8 la pornire, 36 la final, relevant pentru `L-P2` si
  `T-P2`, cele doua celule pe care stratul dinamic le poate devia.

### E6, ablatia memoriei, 4 misiuni

`memory_status = empty`, `memory_loaded = false`, `m3_preferences_count = 0`,
`memory_prefix_included = false` la toate.

**Ambele platforme aleg aceleasi noduri:** `AB-S1` la nodul 9 pe B si pe C, `AB-S3o` la nodul 15 pe
ambele. Cu memoria scoasa, `S1` migreaza de la nodul 0 la 9 si `S3o` de la 14 la 15, identic pe cele
doua platforme.

Trei confirmari `HIGH`; `AB-S3o` pe C a dat `False` `MEDIUM` la `xy = 0.16`, deci a treia neconfirmare
a zilei, si a doua la nodul 15.

**Ablatia este completa, nu partiala.** Cu digestul respins dispare si `build_memory_prefix`, deci din
promptul L3b lipsesc `top_entities`, `top_patterns` si liniile de vizite anterioare. E6 compara „cu
stratul de memorie" cu „fara stratul de memorie".

Digestul gol nu e gol pe toate straturile: M1 are tot 18 entitati, din geojson, iar M4 are o singura
platforma in loc de doua.

### E4, memorie inter-robot, 23 de linii

**E4.0, baza.** Pe C: `P1` la nodul 8, `P2` la nodul 9, ambele `HIGH`. Pe B: **ambele misiuni au esuat
la VLM**, deci faza de baza exista numai pe C.

**E4.1, inducere pe C.** `P1`: 3 rezolvari, nod dominant 10, `consistency = 0.67`. `P2`: 4 rezolvari,
nod dominant 9, `consistency = 0.75`. Pragul este 0.80.

> **Niciuna dintre cele doua preferinte nu a atins pragul de promovare.** Criteriul de oprire declarat
> s-a aplicat: nu s-au adaugat repetitii pana iese. Verificat cu `cluster_key` din codul inghetat, pe
> cele 8 audituri filtrate: `ready = False` la amandoua.

Cele doua au picat din **motive diferite**, care nu se confunda: `P1` a avut si o trunchiere si
alegere instabila, 8 la baza, apoi 10, 10, 5. `P2` a avut **4 rezolvari reusite din 4** si tot nu a
trecut, fiindca a ales noduri diferite. Plafonul de tokeni nu explica inconsistenta.

**E4.2, compilare.** 0 promovari, 2 preferinte M3 detectate dar nepromovate.
**Digestul nu a fost instalat**, prin decizia coordonatorului: un digest cu zero promovari ar fi fost
respins ca `empty` de navigator, iar E4.3 si E5 ar fi rulat fara strat de memorie, adica in alta
conditie decat E4.0.

**E4.3, pe digestul publicat.** Nicio rezolvare la pasul 0, toate reusitele prin `L3b_vlm`, deci
neinstalarea a fost respectata. 4 esecuri VLM din 6 misiuni `P`. Blocul se raporteaza ca **masuratoare
a stabilitatii alegerii L3b intre roboti**, nu ca test de transfer.

`P2` a ales nodul 9 pe C la E4.0, pe C in 3 din 4 la E4.1, si pe B la E4.3, fara memorie si fara
transfer. `P1` a dat 8, 10, 10, 5, apoi 8.

Controale negative: `NEG1` la nodul 9, `NEG2` la nodul 15, ambele escaladate corect.

**Observatie noua: ciclurile sunt re-decizii, nu doar renavigari.** La `NEG2`, ciclul 1 a ales nodul
14 si ciclul 2 nodul 15. La `P2` rep 2, ciclul 1 a ajuns la nodul 9 cu `xy = 2.6`, iar reluarea a
produs un esec L3b nou. Fiecare ciclu inseamna un apel VLM nou, cu risc de esec nou. Diferit de
ciclurile din E3, unde nodul ramanea acelasi si doar `xy` scadea.

### E5, concurenta, 6 misiuni

Toate sase escaladate prin `L3b_vlm`, toate confirmate `HIGH`, `xy` sub 0.21, **zero esecuri**.
B a ales nodul 0 la toate trei perechile, C nodurile 15, 13 si 14. Regiuni disjuncte, fara suprapunere
de traseu. Stare dinamica la pornire: B = 3, C = 4.

| Pereche | B | C | suma |
|---|---|---|---|
| pair1 | 10.07 s | 16.87 s | 26.94 s |
| pair2 | 17.16 s | 9.03 s | 26.19 s |
| pair3 | 18.92 s | 10.79 s | 29.71 s |

In fiecare pereche unul ruleaza la viteza de referinta, circa 9.7 s cu un singur client, si celalalt la
aproape dublu, cu suma aproape constanta. **Cine este primul servit se schimba intre perechi**, deci nu
e efect de platforma. Este serializare pe un singur server ollama.

`queue_ms` nu se poate calcula. Se raporteaza `vlm_ms` per misiune si diferenta in interiorul perechii,
circa 8 secunde constant.

### E4b, a doua inducere, 10 misiuni

Text: `my gloves are wet, where can I dry them`. Referent intentionat `radiator_main`, nodul 9.
Ales dupa criteriu declarat inainte: suprapunere lexicala zero cu ontologia si un singur referent
plauzibil. Nodul 9 fusese deja observat ca atractor in E7 si E6, fapt declarat explicit in amendament.

| Faza | Robot | Rezultat |
|---|---|---|
| `E4b.0` | B | nodul 9, `L3b_vlm`, `HIGH`, `xy = 0.212` — **escaladare, baza valida** |
| `E4b.1` | C | nodul 9 la toate 4 repetitiile, `L3b_vlm`, toate `HIGH` — **consistency 1.00** |
| `E4b.2` | statie | 1 promovare, nod 9, `frequency = 4`, instalata la 17:30 |
| `E4b.3` | B | nodul 9 la toate 4 repetitiile, **`resolution_step = 0`, `L3a_m3_preference`** |
| `E4b.N` | B | `I need to warm up` → **escaladare la L3b**, tot la radiator |

> **Transfer demonstrat cap-coada**, in aceeasi sesiune inghetata: preferinta dobandita pe C prin patru
> rezolvari L3b consistente, compilata de extractorul inghetat, instalata, folosita de B la pasul 0
> fara apel VLM. Acelasi robot escalada inainte de compilare si nu mai escaladeaza dupa.

**Criteriul este pasul, nu nodul.** B alegea deja nodul 9 si fara memorie, deci identitatea destinatiei
nu distinge intre „a folosit preferinta transferata" si „ar fi ales oricum 9". Ce distinge este calea
de rezolvare, de la `L3b_vlm` la `L3a_m3_preference` la pasul 0. Formulat asa inainte de a vedea
rezultatul.

**Controlul negativ confirma mecanismul lexical.** Aceeasi intentie si aceeasi destinatie, dar alte
cuvinte, `J = 0.000` fata de textul promovat: escaladeaza la L3b. Deci M3 potriveste **formularea**, nu
sensul, ceea ce confirma direct predictia 1 din protocolul E7 si limitarea descrisa in D2.

La `E4b.3` s-au rulat **4 repetitii in loc de 3**. Se consemneaza; nu afecteaza concluzia.

`l3a_promotions_ready` contine doar `instruction_examples`, `node_id` si `frequency`. Nu poarta
`consistency`, `method_distribution` sau `ready_for_l3a_promotion`, care exista doar in lista completa
M3. Poarta din documentul E4b, care cere acele campuri **in promovare**, nu e rulabila ca scrisa;
criteriul a fost evaluat de extractor (`1 ready for L3a`) iar consistenta de 1.00 se calculeaza din
audit.

## Ce nu s-a facut

- **Masuratorile manuale la nodul 0, cu ruleta, nu s-au facut.** Nodul 0 ramane fara validare
  independenta, spre deosebire de nodul 8 din ziua 1. `xy` din audit ramane singura sursa pentru cele 9
  sosiri `S1`. Nu se recupereaza.
- `S1` rep 5 pe B, nerulata.
- Numarul de obiecte brute pe B la sfarsitul lui E3.
- Fotografii de scena cu ruleta pentru ancorele esuate: `<da / nu>`

## De completat manual

Ore de pe ceasul robotului, pentru:
- inceputul si sfarsitul fiecarui bloc: `<de completat>`
- cele trei esecuri E7: `<de completat>`
- cele trei esecuri E4.3 nedatate: `<de completat>`
- pornirea fiecarei misiuni E5, cu secunde, pe fiecare platforma: `<de completat>`
- oprirea si repornirea lui C intre blocuri: `<de completat>`

## Inventar

124 de fisiere de audit `audit_20260821_*.jsonl`.

| Bloc | Linii de decizie |
|---|---|
| E3 | 56 (49 executii) |
| E7 | 29 (25 cu decizie, 3 esecuri) |
| E4 | 23 |
| E4b | 10 |
| E5 | 6 |
| E0 | 5 (4 ancore, 1 diagnostic) |
| E6 | 4 |

## Ce se aduce la livrare

- `logs/` complet de pe statie
- `~/arhiva/`, `~/digest_gol/`, `~/digest_E4.2/`, `~/digest_E4b/`, complete, cu M1 pana la M5
- arhivele magaziei dinamice de pe ambii roboti, `~/dyn_arhiva/`
- `md5sum E7_set_sigilat_v2.csv` de dupa bloc, ca dovada de nesigilare
- `~/dovezi/`, cu payloadul si raspunsul ultimului apel de confirmare din E5
- nota de fata, cu campurile manuale completate
