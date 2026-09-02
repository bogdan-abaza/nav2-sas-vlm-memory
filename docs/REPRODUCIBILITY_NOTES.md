# Reproducibility notes for the frozen analyses

These notes record, for a reviewer working from this repository alone, exactly which
reproduction paths are executable from the release, which are not, and why. They change no
frozen artifact: every limitation below concerns the reproduction environment of a sealed
package, never the identity or availability of the evidence behind its reported results.

## Session E core analysis

`analysis/session_e/core/analyze_session_e.py` is executable from the release:

```bash
PYTHONPATH=data/session_e/public_code python3 analysis/session_e/core/analyze_session_e.py \
    --dataset data/session_e --outdir <your-outdir>
```

Two details matter. First, the frozen analyzer predates the publication boundary and looks
for the public SAS text module at its delivery-time location; setting `PYTHONPATH` to
`data/session_e/public_code` (as above) resolves it to the published copy, which is
byte-identical. With that, the analysis reproduces every reported Session E metric
identically from the published evidence. Second, one auxiliary check — the offline replay
of the memory extractor — depends on a production module that is not published. In its
absence the analyzer degrades in a controlled way (the replay block reports it did not run)
and no reproduced Session E metric is affected. The complete source remains available to
the editor and reviewers, in confidence, upon request through the journal.

## A1 — cascade step analysis

A1 is published as a frozen, internally self-verifying supporting analysis. Its original
input set includes non-public material and therefore the analysis is not advertised as
independently rerunnable from the public repository alone. Its checksum manifest, results,
report and analysis script are published and verify as sealed. Its immutable report
preserves the status wording it carried when the analysis was sealed; that wording is
historical and is not rewritten by the release process.

## A2 — M3 matching-parameter sensitivity

A2 is independently reproducible from the public release alone. From the repository root:

```bash
cd analysis/session_e/A2_m3_sensitivity
sha256sum -c A2_CHECKSUMS_SHA256.txt
python3 analyze_A2_m3_sensitivity.py --outdir ./regen
```

The mandatory frozen-setting gate must report `PASS`. The five machine-generated outputs
listed in `analysis/session_e/A2_m3_sensitivity/REPRODUCE.md` regenerate byte-identically.
Python standard library only; no network access or non-public source is required.

## A3 — promotion-threshold sensitivity

The reproduction instructions embedded in the frozen A3 package preserve the
pre-publication analysis environment and therefore refer to `E.zip` and
`session_e_v3.zip`. Those references are historical and are not the normative paths of the
public release. `E.zip` crosses the publication boundary because it contains non-public
production modules, while `session_e_v3.zip` is a superseded analysis snapshot. The current
public Session E evidence and analysis are published under `data/session_e/` and
`analysis/session_e/`, respectively. The frozen A3 package remains self-verifying, but its
original end-to-end reproduction procedure is not publicly executable from the release
alone. This limitation concerns reproduction of the frozen post-hoc analysis workflow, not
the identity or availability of the Session E evidence on which its reported results are
based.

## R210-AN-02 — model-substitution replay

The two frozen acquisition archives of the controlled replay are published inside
`analysis/session_e/r210_model_replay/`, byte-identically:

```
analysis/session_e/r210_model_replay/R2-10_controlled_replay_v3_20260823.tar.gz
  sha256 f59063c0e55fbc9a021c80c97c2e0897f161f620ebb374a887ba0ee4ed54ad04
analysis/session_e/r210_model_replay/R2-10_replay_package_20260823_CORRECTED.zip
  sha256 3b5f8c0dc4d596ea9d94a2bb412f2a9e9c07ffc2323780bc737e0b747623e254
```

Both are listed in the package's own checksum manifest and were published after a full
disclosure scan: they contain the replay prompts, the raw per-model, per-seed outputs, the
environment records and the sealed reference key — and no non-public production source, no
credentials, and no network identifiers. With them, the frozen recompute procedure in the
package's reproduction instructions is executable from the release alone; the one path that
still requires non-public material is the regeneration of the safe Session E reference from
the delivery archive, and the included frozen reference was verified byte-identical to that
regeneration at packaging time.

## Public provenance tools

`tools/build_dataset.py` documents and executes the deterministic construction of the
published Session E dataset from the original delivery, including path translation,
provenance mapping, and generation of the English CSV indexes. The script is public, but
the full reconstruction path requires the original non-public delivery and is therefore not
executable from this repository alone. Verification of the published release itself uses
`data/session_e/CHECKSUMS_PUBLIC.md5`.

`tools/reproduce_digest.py` documents the historical regeneration chain for the compiled
A–C memory digest: raw development logs → memory extractor → digest. The script is public,
but complete regeneration requires the protected memory-extractor production module and
historical development-log inputs outside the public release. Those materials can be made
available to the editor and reviewers in confidence through the journal. The published
digest and startup-digest evidence remain directly inspectable in the release.
