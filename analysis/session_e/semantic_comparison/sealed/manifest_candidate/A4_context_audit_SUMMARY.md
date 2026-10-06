# A4 context audit — summary (CANDIDATE, 4 October 2026)

Script: `harness/context_audit.py` (reads only RC1.1 and the frozen copies `sas_l3a.py` 38b6910f / `sas_text.py` aa211dc7; no model calls).
Output: `A4_context_audit.csv`. Role: **eligibility audit for the historical-context condition H** (protocol §7.3); it is not a gate for the S population.

## Result
- 38 items audited; **28 eligible for H**: E7 20 and E2 8, all with a same-cycle L3b prompt.
- **10 not eligible for H**: M3-1…M3-5 and E7 T-P1, S-P1, H-P1, G-3, G-4 (all resolved deterministically in Session E, hence without a same-cycle prompt). They remain in A4 through condition S.
- For the 28 H items the frozen L3a cascade never reaches the proximity branch, so it does not depend on YOLO coordinates.

## Provenance finding: archive file names are not reset times
Example: `20260821_1008_ubuntu` has `metadata.last_updated` 08:39 UTC; `20260821_1023_saim-desktop` has `last_updated` 2026-08-20 12:59 UTC.
Reset windows are therefore computed from content: [L = `last_updated` of the dump, F = earliest `first_seen` in the next archive of the same platform].

## Why the design uses two conditions
M3 items are, by construction, resolved at Step 0 and never have a same-cycle L3b prompt. Requiring a historically reconstructible dynamic context would remove all FAMILIAR items. The protocol therefore uses S (standardized dynamic-empty context, 38 items, primary) and H (historically observed dynamic context, 28 items, sensitivity), reported separately.
