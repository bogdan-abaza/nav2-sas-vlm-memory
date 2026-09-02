# A2 - Step-0 M3 threshold/margin sensitivity (FROZEN)

Standalone, **public-safe** sensitivity analysis for RAS ROBOT-D-26-01090.
It replays only the documented Step-0 M3 matcher, using the released `sas_text.py`,
the exact Session E digest states, and the released Session E index tables.

It contains and imports **no** production SAS module: no resolver, no navigator, no
negation guard, no memory extractor. `sas_text.py` is the single SAS source file
approved for public release.

Run:

```bash
python3 analyze_A2_m3_sensitivity.py --outdir ./regen
```

The script first executes a **mandatory reproduction gate** at the frozen settings
(`J=0.75`, margin `0.10`) and stops unless the observed Step-0 accept/abstain pattern
and accepted node IDs reproduce exactly. Only then is the sensitivity grid generated.

Population: Session E with E0 excluded (216 decisions), restricted to the 212 with a
non-empty M3 digest. The four E6 memory-ablation decisions have no Step-0 candidate set
and are excluded as not applicable.

Headline results at the frozen operating point:

- 39 Step-0 accepts, all with Jaccard **1.0**; 39/39 accepted node IDs reproduced;
  accept/abstain agreement 212/212.
- Next-highest candidate score is **0.625** - the decision plateau spans thresholds from
  just above 0.625 through 1.0.
- Reverting to the former `J=0.60` admits **four** additional 0.625-overlap candidates
  (two instruction strings, each repeated twice).
- The `0.10` runner-up margin changes **no** decision at the frozen threshold: all 35
  accepted matches with a runner-up have a gap of at least **0.80**.

**Scope warning.** A2 is matcher-level sensitivity, not a counterfactual replay of the
complete deterministic cascade. Counterfactual M3 candidates at lower thresholds are NOT
equivalent to final fast-path resolutions: downstream steps and the location-conflict
guard are outside this analysis. The four `J=0.60` accepts are matcher-level events, not
demonstrated navigation errors.

Artifact note: five files are machine-generated and regenerate byte-identically.
`A2_m3_sensitivity_report.md` is an authored document, not a script output.

Status: **FROZEN** 2026-08-25.
