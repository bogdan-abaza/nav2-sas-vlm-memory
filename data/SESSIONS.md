# Session register

Four named evidence sessions (A, B, C, and E) are represented across two evidence
campaigns. They are not repetitions of one experiment and are not pooled as one
validation population.

Sessions A-C are development-stage evidence collected across evolving
implementations. Session E is the confirmatory physical campaign for frozen
`v4.8-review`; its blocks use block-specific experimental units. E7, specifically,
uses the sealed previously unseen instruction set.

There is no session D.

| session | dates | platforms | code | schema | protocol | audit sessions | decision-bearing runs | decision cycles | resolved-or-blocked |
|---|---|---|---|---|---|---|---|---|---|
| **A** | 2026-04-22 – 2026-04-23 | xplorer-c | v4.7.4, v4.8 | 2.0 | development-stage | 10 | 10 | 85 | 85 |
| **B** | 2026-04-23 | xplorer-b | v4.8 | 2.0 | development-stage | 3 | 3 | 76 | 76 |
| **C** | 2026-04-24 | xplorer-b, xplorer-c | v4.8 | 2.0 | development-stage | 4 | 4 | 4 | 4 |
| **E** | 2026-08-20 – 2026-08-21 | xplorer-b, xplorer-c | v4.8-review | 2.1 | confirmatory frozen-system campaign | 214 | 210 | 226 | 212 |

A record whose `resolution_method` is `escalated` is an unresolved escalation record: an L3b-path attempt that returned
no parseable JSON. It is an attempt, not a completed decision; the two columns above
differ by exactly that count.

## Memory digest per session

Which compiled memory artefact governed which records:

| session | digest (md5 prefix) | stored associations | audit sessions | records |
|---|---|---|---|---|
| A | `a18b610f` | 3 | 9 | 83 |
| A | `41c0a9e7` | 0 | 1 | 2 |
| B | `97241265` | 6 | 3 | 76 |
| C | `97241265` | 6 | 4 | 4 |
| E | `97241265` | 6 | 201 | 214 |
| E | `aba2b031` | 8 | 4 | 3 |
| E | `(none)` | 0 | 4 | 4 |
| E | `eca5dbc8` | 1 | 5 | 5 |

## Where the fast-path rate comes from

The fast-path rate is not a property of the system alone. It is a property of the
system and the instruction distribution it is measured on. Applying the same
fast-path counting definition to the different evidence sets produces the
figures below:

| instruction set | fast path | rate |
|---|---|---|
| Session A, all records | 75 / 85 | **88.2%** |
| Sessions A-C, all records | 155 / 165 | **93.9%** |
| Sessions A-C, scenario subset | 74 / 82 | **90.2%** |
| Session E, all records | 121 / 226 | **53.5%** |
| Session E, excluding failed L3b calls | 121 / 212 | **57.1%** |
| Session E, sealed instruction set (E7) — record-level | 5 / 29 | **17.2%** |

* *Session A, all records* — the set whose rate is the historical 88.2% figure, formerly quoted without naming its denominator
* *Sessions A-C, scenario subset* — the subset the published figures are computed on: instructions matching one of seven scenario patterns. Repositioning commands are excluded; including them raises the rate rather than lowering it.
* *Session E, excluding failed L3b calls* — the convention sessions A-C were forced into: schema 2.0 could not record a failed L3b call, so no denominator from those sessions contains one
* *Session E, sealed instruction set (E7) — record-level* — written and sealed, with its acceptance criteria, before the system saw it. RECORD-LEVEL descriptive rate over the 29 archived cycles; the primary experimental unit is the sealed cell (28 cells; one cell ran twice), and the primary cell-level rate is documented in the canonical core analysis

Two things follow. The historical 88.2% rate is Session A's, not a rate over all
decisions. And no session before E could record a failed L3b call at all: schema
2.0 has no state for one, so every record in sessions A-C resolves to a method
that succeeded. Their denominators exclude failures structurally, not by choice.

## What the audit schema records

Schema 2.0 (sessions A-C) does not carry the fields that identify what produced a
record. Schema 2.1 (session E) does. The difference is visible directly in
`sessions_index.csv` as empty versus populated columns:

| session | audit sessions | audit sessions recording the code commit |
|---|---|---|
| A | 10 | 0 |
| B | 3 | 0 |
| C | 4 | 0 |
| E | 214 | 214 |

The fields absent from schema 2.0 are `git_commit`, `git_dirty`, `geojson_md5`,
`route_graph_md5`, `vlm_model_digest`, `vlm_quantization`, `sas_text_version`,
`gpu_driver_version`, `m3_abstention_margin`, `experiment_id` and `protocol_version`.
They cannot be added retroactively without falsifying the record, and they are not.
What session E demonstrates is that they are recorded now.

## Notes

* **Session A** — Constructed scenarios; memory built up incrementally.
* **Session B** — Constructed scenarios on the second platform using the compiled digest available at startup.
* **Session C** — Concurrent operation of both platforms.
* **Session E** — Frozen v4.8-review physical campaign with block-specific experimental units; E7 alone uses the sealed previously unseen instruction set.

