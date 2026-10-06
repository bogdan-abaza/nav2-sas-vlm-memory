# AprilTag external reference: descriptive summary

**Reproducibility:** re-executable from this release (standard library only).

Recomputes the descriptive summary of the AprilTag map-frame discrepancy from the published detections in `data/session_e/external_reference/`. The script checks the SHA-256 of its inputs first.

```bash
python3 analysis/session_e/apriltag_summary/apriltag_summary.py --out <dir>
```

## Selection
Of 345 images searched, 29 contained a detection and 11 were included. The inclusion decisions are those recorded by the published `apriltag_reference.py`, applied in this order: tag not surveyed (2 excluded), PnP failure (0), mean tag side below 80 px (12), tag with an inconsistent survey (4).

## Results (`results/APRILTAG_SUMMARY.md`, `results/apriltag_summary.json`)
| Component | n | Mean | SD | Min | Max |
|---|---:|---:|---:|---:|---:|
| dx (m) | 11 | +0.208 | 0.042 | +0.137 | +0.276 |
| dy (m) | 11 | +0.030 | 0.060 | −0.049 | +0.127 |
| dyaw (deg) | 11 | −2.30 | 4.26 | −8.99 | +6.99 |

SD is the sample standard deviation (ddof = 1). The included detections comprise 10 repeated observations of tag 3 and 1 of tag 4, with 7 from Xplorer-B and 4 from Xplorer-C. Independent sampling is not established, so no interval of the mean is reported. Per-marker summaries are in the JSON file. These values describe the observed discrepancy; they support no causal conclusion.
