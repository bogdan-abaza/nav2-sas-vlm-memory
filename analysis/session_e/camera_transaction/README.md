# Live image-request transaction on Xplorer-B

**Reproducibility:** the statistics can be recomputed from the published data. Repeating the measurement requires the robot and its camera/context server.

## What is measured
On Xplorer-B, the client transaction from the HTTP image request to the base64 image string being available in memory for L3b. The script repeats the deployed sequence: an HTTP GET of `<context-server-url>/camera`, JSON decoding of the reply and extraction of the base64 image. It times this from just before the request until the image string is in memory. Configuration was recorded before the first transaction and matched Session E (route graph and navigator commit). The measurement was taken on 5 October 2026 from the workstation that runs the navigator. There was no navigation and no model call. JPEG decoding is outside the timer. This client transaction does not measure camera exposure time, frame age or capture-to-client latency.

The result is reported separately from the offline semantic comparison (`analysis/session_e/semantic_comparison/`) and is not added to its decision latencies.

## Result (`CAMERA_PROBE.redacted.json`)
50 pre-specified transactions, all successful, with 50 distinct JPEG payloads by MD5 (mean JPEG size about 97 KB):
- median 57.29 ms;
- Q1–Q3 46.43–68.17 ms;
- range 34.75–211.53 ms.

The first transaction (211.53 ms) is included.

Recompute from the published data:
```bash
python3 -c "import json,statistics as s; v=[t['ms'] for t in json.load(open('analysis/session_e/camera_transaction/CAMERA_PROBE.redacted.json'))['transactions'] if t['ok']]; print(len(v), s.median(v), s.quantiles(v, n=4, method='inclusive'), min(v), max(v))"
```

## Files
- `camera_transaction_probe.py`: the measurement script. In this public copy the private context-server address is replaced by `<context-server-url>`; nothing else is changed. The executed original has SHA-256 `df470b6f3c0e3cf032f43d1c8ca15195bc298b943a59392bef120174967db8e4`, recorded in the data file.
- `CAMERA_PROBE.redacted.json`: configuration, summary and all 50 transactions. The host name is withheld and the private address is replaced by `<context-server-url>`. The SHA-256 of the original file and the rule applied are recorded inside it.
- `CHECKSUMS_SHA256.txt`.
