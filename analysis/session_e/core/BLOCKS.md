# Session E — block register

Session E is not one experiment repeated. It is nine blocks, each isolating one
component and each answering a specific point raised in review. The last line of
each entry is the reason the session exists: it says what, if anything, in
sessions A-C tested the same thing.

| block | records | platforms | intents | what it tests | component | answers |
|---|---|---|---|---|---|---|
| **E0** | 10 | b, c | 2 | Start gate | — | — |
| **E1** | 39 | b, c | 19 | Post-arrival visual confirmation after the ontology correction | L3 post-arrival confirmation; static semantic ontology | R1-9 |
| **E2** | 49 | b, c | 19 | Negation, location conflict, controls | Negation guard (introduced in v4.8-review) | R1-8 |
| **E3** | 56 | b, c | 11 | Verification re-run on the declared experimental unit | L3a cascade; M3 preference matching | R1-2, R1-7 |
| **E4** | 23 | b, c | 4 | Promotion stability: rejection of unstable associations | L5 promotion gate | R1-8, R2-2 |
| **E4b** | 10 | b, c | 2 | Second induction, end to end | L5 promotion; cross-robot digest transfer | R1-8, R2-2 |
| **E5** | 6 | b, c | 3 | Concurrency on the shared VLM server | Shared L3b inference server | R2-6 |
| **E6** | 4 | b, c | 2 | Full semantic-memory ablation | compiled memory digest (M3 matching + M1/M2 prompt prefix) | R1-5, R2-5 |
| **E7** | 29 | b | 28 | Sealed instruction set | Full L3 pipeline on unseen instructions | R1-4, R2-4 |

## What each block measured

### E0 — Start gate

Warm-up and verification that the configured digest, graph and ontology match the sealed values before any measured run.

**Records** 10 across xplorer-b, xplorer-c, 2 distinct intents (median 5.0 repetitions each).  
**Resolution** `L3a_deterministic` 5, `L3a_m3_preference` 4, `L3b_vlm` 1.  
**Fast path** 9/10 = 90.0% [59.6, 98.2].  
**L3b** 1 call, 0 without parseable JSON (0.0%).  

*In sessions A-C:* —

> **Excluded from all reported rates.** It is a configuration check, not a measurement.

### E1 — Post-arrival visual confirmation after the ontology correction

Re-test of arrival confirmation once fire_hydrant_cb202 was corrected to fire_extinguisher_cb202, including the arm in which the extinguisher was physically removed.

**Records** 39 across xplorer-b, xplorer-c, 19 distinct intents (median 1.0 repetitions each).  
**Resolution** `L3a_deterministic` 31, `L3a_m3_preference` 8.  
**Fast path** 39/39 = 100.0% [91.0, 100.0].  

*In sessions A-C:* Confirmation was reported but never re-tested against a corrected ontology, and no arm varied the physical referent.

### E2 — Negation, location conflict, controls

Negated instructions, instructions whose location referent conflicts with the semantic referent, and matched controls.

**Records** 49 across xplorer-b, xplorer-c, 19 distinct intents (median 2.0 repetitions each).  
**Resolution** `L3b_vlm_negation_blocked` 22, `L3b_vlm` 15, `escalated` 4, `L3a_deterministic` 4, `L3a_m3_preference` 4.  
**Fast path** 8/49 = 16.3% [8.5, 29.0].  
**L3b** 19 calls, 4 without parseable JSON (21.1%).  
**Negation guard** blocked 22 of them.  

*How to read this block's rate:* A low fast-path rate is the intended outcome. A negated instruction should not be resolved deterministically; escalation or a block is the correct behaviour.

*In sessions A-C:* The mechanism did not exist. No record in sessions A-C can show negation handling of any kind.

### E3 — Verification re-run on the declared experimental unit

Repetition of resolved instructions with the unit of analysis declared in advance, so repeated measures can be grouped.

**Records** 56 across xplorer-b, xplorer-c, 11 distinct intents (median 4.0 repetitions each).  
**Resolution** `L3a_deterministic` 33, `L3a_m3_preference` 23.  
**Fast path** 56/56 = 100.0% [93.6, 100.0].  

*In sessions A-C:* Repetitions exist but no unit of analysis was declared, so they were counted as independent observations.

### E4 — Promotion stability: rejection of unstable associations

Whether repeated L3b resolutions of the same instruction converge closely enough to be promoted into deterministic memory. Both candidates fell below the consistency threshold and neither was promoted, so this block does not demonstrate transfer; E4b does.

**Records** 23 across xplorer-b, xplorer-c, 4 distinct intents (median 5.5 repetitions each).  
**Resolution** `L3b_vlm` 16, `escalated` 7.  
**Fast path** 0/23 = 0.0% [0.0, 14.3].  
**L3b** 23 calls, 7 without parseable JSON (30.4%).  

*How to read this block's rate:* Fast path is 0% by construction: the block issues L3b calls in order to accumulate association candidates.

*In sessions A-C:* Session B ran on the digest compiled from session A, but the induction and the transfer were not run as one controlled sequence.

### E4b — Second induction, end to end

The same transfer repeated as a single uninterrupted chain, with the digest recompiled and reinstalled between platforms.

**Records** 10 across xplorer-b, xplorer-c, 2 distinct intents (median 5.0 repetitions each).  
**Resolution** `L3b_vlm` 6, `L3a_m3_preference` 4.  
**Fast path** 4/10 = 40.0% [16.8, 68.7].  
**L3b** 6 calls, 0 without parseable JSON (0.0%).  

*How to read this block's rate:* The fast-path records are the point of the block: they are the transferred preference being served at cascade step 0 on the second platform.

*In sessions A-C:* —

### E5 — Concurrency on the shared VLM server

Both platforms issuing VLM requests against one server, with destinations chosen so the routes cannot intersect.

**Records** 6 across xplorer-b, xplorer-c, 3 distinct intents (median 2.0 repetitions each).  
**Resolution** `L3b_vlm` 6.  
**Fast path** 0/6 = 0.0% [0.0, 39.0].  
**L3b** 6 calls, 0 without parseable JSON (0.0%).  

*How to read this block's rate:* Fast path is 0% by construction; the block issues VLM calls deliberately to load the shared server.

*In sessions A-C:* Session C ran both platforms concurrently, but with four decisions and no latency comparison against single-platform operation.

### E6 — Full semantic-memory ablation

The same instructions with the compiled digest removed. That takes away M3 step-0 matching AND the M1/M2 prefix of the L3b prompt, so it ablates the whole memory layer, not M3 in isolation.

**Records** 4 across xplorer-b, xplorer-c, 2 distinct intents (median 2.0 repetitions each).  
**Resolution** `L3b_vlm` 4.  
**Fast path** 0/4 = 0.0% [0.0, 49.0].  
**L3b** 4 calls, 0 without parseable JSON (0.0%).  

*How to read this block's rate:* Fast path is 0% by construction: the digest is removed, so no M3 preference can match.

*In sessions A-C:* Never performed.

### E7 — Sealed instruction set

Instructions written from a university-corridor repertoire and sealed, with their acceptance criteria, before the system saw them.

**Records** 29 across xplorer-b, 28 distinct intents (median 1.0 repetitions each).  
**Resolution** `L3b_vlm` 21, `L3a_deterministic` 5, `escalated` 3.  
**Fast-path coverage (primary, per sealed instruction cell)** 5/28 = 17.9% [7.9, 35.6].  
*29 decision cycles represent 28 sealed cells; one cell was executed twice; the record-level figure 5/29 = 17.2% is descriptive only.*  
**L3b** 24 calls, 3 without parseable JSON (12.5%).  

*How to read this block's rate:* The only block whose fast-path rate estimates performance on instructions the system had not seen.

*In sessions A-C:* Never performed. Every instruction in sessions A-C was constructed around the scenarios being demonstrated.

> **Single platform.** This block ran only on xplorer-b. Its result has no replication on the second robot, and is reported as such.

## Why rates are reported per block

The session-wide fast-path rate is an artefact of how many records each block contributed, not a property of the system. Blocks E1 and E3 issued no VLM call at all, while E7 escalated most of its instructions. Rates must be read per block; the aggregate is reported only alongside this composition.

| block | records | fast path | L3b calls | how to read it |
|---|---|---|---|---|
| E0 | 10 | 90.0% (9/10 records) | 1 | measured |
| E1 | 39 | 100.0% (39/39 records) | 0 | measured |
| E2 | 49 | 16.3% (8/49 records) | 19 | A low fast-path rate is the intended outcome. A negated instruction should not be resolved deterministically; escalation or a block is the correct behaviour. |
| E3 | 56 | 100.0% (56/56 records) | 0 | measured |
| E4 | 23 | 0.0% (0/23 records) | 23 | Fast path is 0% by construction: the block issues L3b calls in order to accumulate association candidates. |
| E4b | 10 | 40.0% (4/10 records) | 6 | The fast-path records are the point of the block: they are the transferred preference being served at cascade step 0 on the second platform. |
| E5 | 6 | 0.0% (0/6 records) | 6 | Fast path is 0% by construction; the block issues VLM calls deliberately to load the shared server. |
| E6 | 4 | 0.0% (0/4 records) | 4 | Fast path is 0% by construction: the digest is removed, so no M3 preference can match. |
| E7 | 29 | 17.9% (5/28 sealed instruction cell) | 24 | The only block whose fast-path rate estimates performance on instructions the system had not seen. |

