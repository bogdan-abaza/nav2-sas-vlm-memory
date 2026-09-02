# Provenance — sas_text.py

`sas_text.py` is the only SAS production module approved for publication
under the frozen publication policy of this release (see `docs/PUBLICATION_SCOPE.md`). At the public boundary the
delivery `code/` directories are replaced by this `public_code/` directory; the remaining
delivery modules are not published.

- Source: the delivery code directory of day1_20260820, byte-identical to its day2_20260821 counterpart
  (verified at build time).
- sha256 `aa211dc76cb2f19f3ff3c9b27c7ba56242b04a4a1ef2fc10d6ad6ad14eb005b1`
- `COMMITS.txt` (same byte-identity across both days): sha256 `fbfe572b4e44d718161b43780a26645d60e6590d488a5ea0134dfe0a740b797c`
- The 2 further copies of `sas_text.py` embedded in the frozen supporting analyses under
  `analysis/session_e/` are byte-identical to this file, asserted at build time.
- Built by the repository build tool (gate-side, not published), 29 August 2026, from the live delivery trees.
