# Note de rulaj, ziua 1, 20 august 2026

Ce nu se vede din audituri și nu se reconstituie mai târziu.
Câmpurile marcate `<...>` se completează de mână înainte de livrare.

## Identitate

| Câmp | Valoare |
|---|---|
| `git_commit` | `f973aa0c4920e47cdd85d7e4e263e3b66fb41ddc`, arbore curat |
| `geojson_md5` (v2 activ) | `2e48375071c0e4ea7cd38c0e48ef97c5` |
| md5 fișier digest | `97241265217eb4b08e26fb718eb21f40` |
| `content_md5` digest (cel din audit) | `0fd61f9e82e8fe6991f0311014384e0c` |
| `route_graph_md5` servit de context | `b5736e070dfd9ced98f821c1e34255c8` |
| `route_graph_md5` calculat de navigator | `e0130b78b00ec55822dbc39a41429817` |
| `route_graph` md5 pe disc | `440522bc9f0c32997698310f680bfb89` |
| `protocol_version` | `E-2026-09` |
| `MERGE_DISTANCE_M` / `YOLO_DEDUP_RADIUS_M` / `YOLO_MIN_OBSERVATIONS` | 1.0 / 1.5 / 3 |

Cele trei hash-uri de graf provin din trei serializări ale aceluiași graf de 24 de noduri.
`check_graph_v2.sh` a dat cod 0 cu verdictul „DIFERIT, dar echivalent" pe ambele platforme.

Cele două hash-uri de digest: `content_md5` este calculat pe conținutul stabil, fără
`generated_at`, identic în `memory_extractor.py` (linia 641) și în navigator (linia 1058).
**Pentru E4 contează `content_md5`**, nu md5-ul de fișier, care se schimbă la fiecare regenerare.

## Amendamentul A9, stratul dinamic

Navigatorul citește obiectele dinamice live de la `/context` și le trece prin
`_filter_yolo_objects`: prag de observații, suprimarea claselor cu corespondent static,
dedup spațial la 1.5 m. Măsurat pe C înainte de campanie: **527 brute, 83 supraviețuiesc**.
Cele 322 suprimate sunt `chair` și `potted plant`. Ce trece sunt clase COCO fără corespondent
static (`bed`, `suitcase`, `parking meter`, `stop sign`, `refrigerator`, `dining table`,
`bench`, `tv`), plus un `toilet` și un `sink`, care ating H2.1 și H2.2 fiindcă ontologia are
clasa `restroom`, nu `toilet`.

Pragul de 3 este inoperant: numărătoarea e pe cadru, valorile reale sunt de ordinul miilor.
Codul e înghețat, deci singura pârghie e starea de pornire.

**Decizie:** magazia se arhivează și se golește la puncte declarate în avans.
`semantic_localizer` rămâne pornit, deci magazia se reumple în timpul blocurilor lungi.
Se declară ca limitare.

### Stare moștenită și rata de acumulare

| Moment | Platformă | Obiecte brute |
|---|---|---|
| înainte de campanie (acumulat 19 aug) | C | 527 |
| înainte de campanie (acumulat 19 aug) | B | 380 |
| înainte de E2, după 20 de misiuni | C | 54 |
| înainte de E2 | B | 0 (localizer oprit, vezi mai jos) |

Rata pe C: circa 2.7 obiecte brute pe misiune.

## Abateri de configurație

- **Ancora `AD` și cele patru `E1bP` de pe B au rulat cu `semantic_localizer` oprit**, deci cu
  strat dinamic gol. Pe C aceleași misiuni au rulat cu localizerul pornit. Nu afectează
  concluzia E1b: `fire extinguisher` e clasă statică, suprimată de stadiul 2 al filtrului,
  iar separarea 4 la 4 s-a obținut identic pe ambele platforme. Se consemnează fiindcă e o
  diferență de configurație într-un bloc care compară platformele.
- **`blocuri.env` nu cunoaște `E0`, `E6`, `E7`.** Pentru ancore s-a exportat direct
  `EXPERIMENT_ID=E0`. Aceeași soluție va fi necesară mâine pentru E6 și E7.
- **Serverul de context de pe B avea în YAML căile lui C** (`/home/saim/...`), moștenite la
  copierea pachetului. S-a corectat la cald cu `ros2 param set`. Parametrii se pierd la fiecare
  repornire a nodului și au fost repuși de fiecare dată.
- **`preflight_audit_v2.py` nu aplică excepția `pose_based`** pentru nodurile 0 și 4, deși
  amendamentul o prevede. Dă cod 1 cu `raw_response_truncated` și `expected_cue_text` marcate
  ABSENT, deși `confirmation_method` este `pose_based` și absența e legitimă. Fals pozitiv
  cunoscut. Poarta autoritativă rămâne `check_graph_v2.sh`.
- **Ordinea platformelor la E2: B înainte de C.**

## Reluări și rulaje abandonate

| Misiune | Ce s-a întâmplat | Decizie |
|---|---|---|
| `SW14` | cădere AMCL în timpul execuției | relansată, cauză externă; în analiză intră execuția completă; ambele rămân în log |
| ancora de seară, C | publicată cu instrucțiune greșită (`main entrance` în loc de instrucțiunea din fișă) | rulaj abandonat, relansat cu `repetition_index` 2; auditul greșit rămâne în log |

Ora reluării `SW14`: `<de completat>`
Ora rulajului abandonat pe C: `<de completat>`

## Eșecuri de VLM, nerelansate

Toate patru sunt eșecuri de parsare a răspunsului L3b, pe instrucțiunea de excludere în
română. Cauză internă sistemului măsurat, deci se raportează, nu se reia.

| Misiune | Ora | Eroare |
|---|---|---|
| `X03` r1 | `<de completat>` | `raspuns L3b fara JSON (done_reason=length, eval_count=500)`, text tăiat în timp ce enumera nodurile 0 și 4 |
| `E1-11` | 15:42 | `Expecting property name enclosed in double quotes: line 1 column 2` |
| `E2-14` | 15:44 | `Expecting value: line 3 column 11 (char 26)` |
| `E2-17` | 15:49 | `raspuns L3b fara JSON (done_reason=length, eval_count=500)` |

Tiparul e consistent: modelul răspunde în proză despre nodurile refuzate în loc să emită JSON,
iar la două din patru e tăiat de limita de 500 de tokeni de evaluare. Se raportează ca mod de
eșec al L3b la excluderea formulată în română, nu ca zgomot.

**Consecință pentru H2.4:** cele 16 misiuni de excludere planificate (4 intenții x 2 repetiții
x 2 platforme) au produs 12 observații utilizabile. Plafonul se calculează la n=12, iar cele 4
eșecuri se raportează separat, ca rezultat despre fiabilitatea L3b.

Din cele 12: `nod = -1` (abținere) la nouă, rezolvare la nodul 9 la două, iar `X04` r1 pe C a
mers întâi la nodul 15, apoi la 9, în două cicluri.
`resolution_step` nu se scrie la excluderi, este `None` peste tot.

## Rezultate, ziua 1

**E1s, baleierea, 15 din 15.** `nod = exp` la toate, zero confuzii de navigare, toate `xy` sub
0.27 m. Un singur eșec de confirmare: `SW19`, nodul 19, `confirmed False`, `MEDIUM`, la
`xy = 0.167`. `expected_cue_text` a conținut numai `plant_3`, deși nodul 19 are două obiecte în
ontologie. Merită verificat de ce apare unul singur.

Cicluri multiple: `SW15` trei cicluri în aceeași execuție (`xy` intermediar 5.21 și 5.59 m),
`SW14` două linii, dintre care una din execuția abandonată. La analiză cele două cazuri nu se
numără la fel; `SW15` are cicluri interne reale, `SW14` are o execuție abandonată.

**E1b, 2x2 închis.** Extinctor prezent: 4 din 4 confirmate, `HIGH`. Extinctor absent: 4 din 4
neconfirmate, `LOW`. Ambele platforme, aceeași zi, același cod, aceeași etichetă în ontologie.
Toate `xy` sub 0.22 m. Concluzie: confirmarea urmărește obiectul, nu eticheta. Cele 0 din 15 de
pe 19 august erau răspunsul corect la o scenă goală.

Ora punerii extinctorului: `<de completat>`
Ora ridicării: `<de completat>`
Ora repunerii după E1b: `<de completat>`
Fotografii de scenă, ambele stări, cu ruleta: `<da / nu>`

**Poarta de sfârșit de zi: zero încălcări H2.1 și H2.2.** Remediul de la unitatea 2b ține pe
date noi, pe ambele platforme. **E3 este liber pentru ziua 2.**

## Măsurători manuale

Nodul 8, din 8 sosiri E1b plus ancorele: `<de completat în manual_measurements.csv>`
Nodul 0 se măsoară în ziua 2, din 10 sosiri S1 plus 2 A01.

## De pregătit pentru ziua 2

- Grila E7, 28 de celule, completată de o singură persoană, o singură dată, fotografiată, cu
  `md5` consemnat **înainte** de prima misiune.
- Verificare de independență: un coleg citește cele 28 și marchează câte sună a manual de robot.
- Verificare că niciuna dintre cele 28 nu coincide cu `P1` sau `P2` din E4.
- Digestul gol pentru E6, cu zero promovări, cu `content_md5` consemnat.
- Verificare înainte de E4.0 că digestul de pornire nu conține deja `deliveries` și
  `quiet corner`.
- Eventual, adăugarea blocurilor `E0`, `E6`, `E7` în `blocuri.env`, ca să nu depindă de un
  export manual la fiecare bloc.
