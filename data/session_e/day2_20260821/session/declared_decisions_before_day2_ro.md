# Decizii declarate înainte de ziua 2 — sesiunea E

**Data:** 20 august 2026, seara. Consemnate **înainte** de prima misiune a zilei 2.
Se copiază în manifestul sesiunii.

---

## D1 · Compilarea digestului la faza E4.2 se face din log-urile zilei 2, exclusiv

`memory_extractor.py` nu are funcție de îmbinare: construiește un digest **complet nou** din
auditurile care i se dau. Alegerea sursei nu e un detaliu de operare, ci determină conținutul
memoriei pe care rulează E4.3 și E5.

**Decizie:** numai `audit_20260821_*.jsonl`.

**Consecință declarată:** digestul rezultat conține **exact două** preferințe — cele două induse pe
XPLORER-C în faza E4.1. Cele șase promovări din digestul publicat `97241265…` **nu se transferă**,
fiindcă provin din sesiunile din aprilie. Digestul de după E4.2 **nu** este „cel publicat plus două".

**Motiv:** log-urile zilei 1 conțin cele zece misiuni de excludere din E2. Rulând extractorul
înghețat pe livrarea zilei 1 rezultă o singură promovare, iar aceea este o **abținere**
(`node_id = -1`, `frequency = 10`). Vezi D2.

**Verificare la momentul compilării:** exact 2 promovări, ambele obținute prin L3b, niciuna la
`node_id = -1`, nodurile identice cu cele alese de C în E4.1. Altfel E4.3 nu pornește.

---

## D2 · Rezultat offline: regula de promovare M3 nu filtrează abținerile

Obținut prin rularea extractorului înghețat (`f973aa0`) peste log-urile zilei 1. Nu necesită timp
de robot și nu modifică nimic din sistemul măsurat.

Cele zece misiuni de excludere din E2 au înregistrat `node_id = -1` de zece ori, cu aceeași
instrucțiune, rezolvate prin L3b. Criteriul de promovare — `frequency ≥ 3 ∧ consistency ≥ 0.8 ∧
≥ 1 rezolvare L3b` — s-a îndeplinit. Nimic nu exclude nodul −1.

Rezultatul: **o abținere repetată devine preferință M3**, cu exemplarul
*„I would not go to a place to take a short break for personal needs"*.

Mai departe, potrivirea M3 este **oarbă la negație**:

```
tokeni abtinere : break, needs, not, personal, place, short, take
tokeni S1       : break, needs,      personal, place, short, take
diferenta       : "not"                    ->  J = 0.857
```

`would` este stopword, `not` nu este. Forma negată și cea afirmativă a aceleiași cereri sunt, pentru
stratul de memorie, **86% identice** — peste pragul de 0.75. Poarta de negație operează separat, în
amonte, pe cuvinte brute; **preferința stocată** nu poartă însă niciun semn al negației.

Consecință: un digest care conține ambele forme le pune în competiție, iar ceea ce le separă este
marja de abținere de 0.10 — `1.000` față de `0.857`, adică `0.143`. Foarte aproape de prag.

Se raportează ca limitare a stratului de memorie, relevantă pentru întrebările lui R2.

---

## D3 · Convenția de calcul pentru J

`J` se calculează cu `sas_text.tokenize` și `sas_text.jaccard` din `f973aa0` — aceleași funcții pe
care `sas_l3a.py` le importă pentru pasul 0. Numărarea pe cuvinte brute dă alte valori, fiindcă
`tokenize` elimină stopwords și aplică `RO_CLASS_ALIASES`. **Valoarea raportată este cea a codului.**

Unde contează pragul sau marja, se raportează rezultatul lui `match_m3_preference`, care agregă pe
nod, nu Jaccard-ul brut exemplar cu exemplar.

---

## D1a · Sursa se restrânge la faza E4.1

**Data:** 21 august 2026, înainte de prima misiune. Corectează D1.

Sursa pentru compilarea digestului la faza E4.2 se restrânge la **faza E4.1**, nu la ziua 2 în
întregime, cum prevedea D1.

**Motiv verificat în codul înghețat `f973aa0`:** `extract_m3` primește toate deciziile, fără filtru
pe metodă, și grupează pe `normalize_instruction`, delegată la `sas_text.cluster_key`, deci pe
tokenii textului și pe nimic altceva.

`AB-S1` și `AB-S3o` din E6 au text identic cu `S1` și `S3o` din E3 și cad în aceleași buckete,
furnizându-le rezolvarea `L3b_vlm` care le lipsea. Cu `M3_PROMOTION_THRESHOLD = 3`, ar rezulta cel
puțin patru promovări în loc de două.

Restrângerea la E4.1 elimină și contaminarea de la E4.0, care rulează aceleași două texte cu
escaladare și ar putea coborî `consistency` sub 0.8 chiar pe preferințele vizate.

**Verificat rulând `extract_m3` pe un set care reproduce ziua 2:**

| Exemplar | freq | consistency | L3b | promovat |
|---|---|---|---|---|
| `go to a place to take a short break…` (S1) | 12 | 1.00 | 2 | **da** |
| `It is too hot in here…` (S3o) | 6 | 1.00 | 2 | **da** |
| `take me to the place where deliveries arrive` (P1) | 6 | **0.83** | 6 | da, la limită |

`P1` la 0.83 este la trei sutimi de prag. Dacă ambele misiuni E4.0 nimeresc alt nod decât E4.1,
`consistency` scade la **0.67** și `P1` nu se promovează deloc — E4 ar eșua din cauza sursei de
compilare, nu a sistemului. Restrâns la E4.1: `freq 4`, `consistency 1.00`, `L3b 4`.

**Filtrarea pe fișier e sigură:** verificat pe cele 90 de audituri ale zilei 1, niciunul nu amestecă
două `experiment_id` — 88 cu un singur bloc, 2 fără decizii.

**Consecința declarată din D1 rămâne neschimbată:** digestul de după E4.2 conține exact două
preferințe și nu este „cel publicat plus două".

---

## D4 · Corecția constantei `content_md5`

**Data:** 21 august 2026, după rularea porții A1–A4.

Fișierul `config/digest_hashes.txt` din livrarea zilei 1 conținea
`content_md5 = bdc89fcf1e17f8c577a941cd80be70ab`, etichetat „cel din audit". **Eticheta era falsă.**
Auditurile zilei 1 înregistrează `digest_content_md5 = 0fd61f9e82e8fe6991f0311014384e0c` în
**93 din 93** de înregistrări. Constanta greșită fusese preluată în `verifica_start.sh` și în fișă,
producând cod 1 la poarta de pornire.

**Nu există două convenții de hash în cod.** Navigatorul (linia 1058) și extractorul (linia 641)
exclud amândouă `generated_at` și `content_md5`, cu `sort_keys=True` și `separators=(',',':')`.
Pe digestul publicat problema nici nu se pune: fișierul **nu conține** cheia `content_md5`, deci
ambele moduri de calcul dau aceeași valoare.

```
md5 fisier                         : 97241265217eb4b08e26fb718eb21f40
exclude generated_at + content_md5 : 0fd61f9e82e8fe6991f0311014384e0c
exclude doar generated_at          : 0fd61f9e82e8fe6991f0311014384e0c
content_md5 scris in fisier        : cheia lipseste
```

Corectat în: `verifica_start.sh`, antetul fișei, poarta E6 → E4, și `digest_hashes_CORECTAT.txt`.
După corecție, `verifica_start.sh` trebuie să iasă cu **cod 0**, fără abateri cunoscute.

**Consecință pentru E4.2:** digestul produs de extractor **conține** cheia `content_md5`, spre
deosebire de cel publicat. Valoarea scrisă în fișier trebuie să fie identică cu
`digest_content_md5` din audit. Diferența ar însemna că una dintre cele două implementări a fost
atinsă, iar ipoteza de îngheț cade. Verificarea a fost adăugată ca punct 5 în poarta de după E4.2.
