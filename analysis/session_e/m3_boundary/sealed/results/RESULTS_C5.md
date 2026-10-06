# C5 — M3 Decision-Boundary Challenge: results (data only)

Run 2026-10-05T06:25:01Z · sealed set C5_SEAL.json sha256 097953300fb68e737d433a03ce3498e9627e6fc23f80c624727c3dcf38288f9c

Diagnostic set constructed with access to similarity scores; labels assigned before each candidate was scored and reviewed on sheets without scores or decisions. Reported separately from A4; not pooled.

| Matcher | Family | n | correct accept | wrong accept | abstention (label = node) | correct abstention (label = abstain) |
|---|---|---|---|---|---|---|
| EXACT | F1 | 16 | 0 | 0 | 16 | 0 |
| EXACT | F2 | 15 | 0 | 0 | 2 | 13 |
| EXACT | F3 | 16 | 0 | 0 | 5 | 11 |
| EXACT | ALL | 47 | 0 | 0 | 23 | 24 |
| JACCARD_0.75_0.10 | F1 | 16 | 10 | 0 | 6 | 0 |
| JACCARD_0.75_0.10 | F2 | 15 | 0 | 9 | 2 | 4 |
| JACCARD_0.75_0.10 | F3 | 16 | 4 | 2 | 1 | 9 |
| JACCARD_0.75_0.10 | ALL | 47 | 14 | 11 | 9 | 13 |
| JACCARD_0.60_0.10_ref | F1 | 16 | 14 | 0 | 2 | 0 |
| JACCARD_0.60_0.10_ref | F2 | 15 | 0 | 13 | 1 | 1 |
| JACCARD_0.60_0.10_ref | F3 | 16 | 4 | 2 | 1 | 9 |
| JACCARD_0.60_0.10_ref | ALL | 47 | 18 | 15 | 4 | 10 |

## Boundary bands — floating-point check (JACCARD 0.75/0.10, as implemented)

| Item | Band | exact top | float top | exact gap | float gap | status |
|---|---|---|---|---|---|---|
| C011 | J=3/4 | 3/4 | 0.75 | 19/36 | 0.5277777777777778 | accept |
| C012 | J=3/4 | 3/4 | 0.75 | 1/2 | 0.5 | accept |
| C033 | J=3/4 | 3/4 | 0.75 | 19/36 | 0.5277777777777778 | accept |
| C034 | J=3/4 | 3/4 | 0.75 | 3/4 | 0.75 | accept |
| C051 | gap=1/10 | 1/1 | 1.0 | 1/10 | 0.09999999999999998 | abstain_ambiguous_margin |
| C052 | gap=1/10 | 1/1 | 1.0 | 1/10 | 0.09999999999999998 | abstain_ambiguous_margin |
| C053 | gap=1/10 | 1/1 | 1.0 | 1/10 | 0.09999999999999998 | abstain_ambiguous_margin |
| C054 | gap=1/10 | 1/1 | 1.0 | 1/10 | 0.09999999999999998 | abstain_ambiguous_margin |
| C063 | J=3/4 | 3/4 | 0.75 | 29/44 | 0.6590909090909091 | accept |
| C070 | J=3/4 | 3/4 | 0.75 | 29/44 | 0.6590909090909091 | accept |

N3 items (C053, C054) use a challenge-index association whose node is semantically questionable (Amendment 02, B2): flagged in per_item.csv (`n3_index_note`).
