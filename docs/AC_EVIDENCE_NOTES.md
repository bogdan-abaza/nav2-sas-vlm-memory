# Sessions A–C — evidence notes

Machine-verifiable notes on the development-stage evidence. Every figure in this document was
recomputed from the published files on 29 August 2026; the two companion tables,
`docs/ac_startup_digest_map.csv` and `docs/ac_inclusion_funnel.csv`, are generated directly
from the seventeen published audit logs.

## 1. Startup digest ledger

Each of the seventeen Sessions A–C audit logs opens with a startup record that names the
compiled memory digest loaded for that run: its MD5 hash, byte size, load status, and the
number of stored associations. Three digests appear (full per-start mapping in
`docs/ac_startup_digest_map.csv`):

| Digest (MD5) | Starts | Stored associations | Status |
|---|---|---|---|
| `97241265…` | 7 — all Session B and Session C starts | 6 | published: `data/memory/memory_digest.json`, the delivered snapshot |
| `a18b610f…` | 9 — Session A starts | 3 | published as a **verifiable regeneration**: `data/memory/memory_digest_a18b610f.json` |
| `41c0a9e7…` | 1 — one Session A start | 0 | **unavailable** — documented below |

**The regenerated Session-A digest.** The delivery archives do not preserve the digest file
loaded at the nine Session-A starts. The repository therefore publishes a regeneration,
rebuilt from the raw logs: its MD5 (`a18b610f06e9ded2e89f7d64bfc6357c`) equals the hash
recorded independently at each of those nine starts, and its size (1,499 bytes) equals the
recorded startup size field. It is published as a regeneration, not as the delivered
original, and this distinction is deliberate.

**Auditability versus regenerability.** The use of the six-association digest at every
Session B and C start is fully auditable: each startup record names its hash and size, and
the published file matches them. The digest itself, however, is not end-to-end regenerable
from the seventeen A–C audit logs alone: its compilation consumed extractor state that the
audit logs do not carry. Auditable and regenerable are distinct properties, and only the
first is claimed for this artifact.

**The zero-association digest.** One Session-A start loaded a digest with zero stored
associations, hash `41c0a9e7…`. No copy of that file is available in any preserved source; it
is documented here as unavailable rather than reconstructed.

## 2. Inclusion funnel for the public audit population

The seventeen audit logs contain **165 logged decision records: 85 (Session A) + 76
(Session B) + 4 (Session C)**. Of these, **82 — 37 + 41 + 4 — are scenario-classified**: they
belong to the seven controlled scenarios recognised by the `classify()` function of the
published `analysis/figures/data_loader.py` module. The remaining **83** fall outside the
scenario subset: repeated repositioning commands (one destination command repeated 47 times,
another 28 times, a third 6 times) and two VLM calls for an instruction that no scenario
covers. The full per-scenario and per-instruction breakdown, by session, is in
`docs/ac_inclusion_funnel.csv`; any published scenario-level rate uses the 82-record subset
as its denominator, and any whole-population figure uses 165, never a mixture.

## 3. Historical memory counters

The delivered digest `data/memory/memory_digest.json` carries a `global_stats` block reading
`total_tasks: 373` and `success_rate: 0.29`. These are cumulative development-history
counters of the memory layer, aggregated over the whole development period that preceded the
digest's compilation. They are not outcomes of Sessions A–C or of Session E, they are not
comparable to any session-level rate reported by this repository or the paper, and no
published result is derived from them. They are preserved because the digest is published
byte-identically.

## 4. Version fields at startup

The startup records also carry the navigator version per run (see the mapping table):
Session A spans `v4.7.4` and `v4.8` starts; Sessions B and C ran `v4.8` throughout. Run-level
version provenance comes from these startup records; the snapshot-level version field inside
memory artifacts is not a run-level source (see `docs/PUBLICATION_SCOPE.md`).

## 5. Historical ontology label

The delivered A–C configuration `config/semantic_objects_static.geojson` names one object
`fire_hydrant_cb202`, class "fire hydrant". The physical object is a fire extinguisher. The
label is a historical ontology error of the delivered map, identified during the revision:
it explains a subset of the failed visual confirmations in Session B, where the model saw
and described the object correctly while the map named it differently. The delivered
configuration and the A–C logs that reference the label are published byte-identically and
are not silently altered; the corrected ontology
(`fire_extinguisher_cb202`, class "fire extinguisher") is used by the Session E
configuration, `data/session_e/day1_20260820/config/semantic_objects_static_v2.geojson`.
