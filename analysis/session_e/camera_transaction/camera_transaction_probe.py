#!/usr/bin/env python3
"""Live image-acquisition transaction on Xplorer-B: `request image -> image available to L3b`.

Pre-specified before the first measured transaction (5 Oct 2026). Descriptive only; not pooled with the offline comparison.

What is measured, and why it matches the deployed path. In the frozen navigator (v4.8-review), L3b obtains its image with
`fetch_camera_b64()`: an HTTP GET of `{CONTEXT_SERVER_URL}/camera` (timeout 10 s), `json.loads` of the reply, and
`cam.get('data', '')`. The returned base64 string goes directly into the VLM payload. This script repeats exactly that
sequence from the AI station (the host on which the navigator ran) and times it with `time.perf_counter_ns()` from just
before the request is opened until the base64 string is in memory. After the timer it decodes the string to check that a
JPEG arrived, and records its size and md5. No navigation, no ROS command, no VLM call.

Protocol:
  - N = 50 measured transactions, all reported (none discarded); idle gap 1.0 s between transactions.
  - A failed transaction (exception, empty data, not a JPEG) is recorded as a failure and counted; it is not retried.
  - Reported: median, IQR, min-max of all successful transactions, plus the first transaction and the failure count,
    and the number of distinct frames (md5) to show whether the server returned fresh or repeated frames.
  - Configuration recorded before the first transaction: host, Python, the context-server URL, canonical md5 of `{URL}/graph` (sorted-key JSON, as the deployed
    `_remote_graph_md5()`; Session E: e0130b78b00ec55822dbc39a41429817), and, if `--repo` is given, `git rev-parse HEAD` of the directory holding the
    deployed navigator file (as the deployed audit header) (Session E: f973aa0c4920e47cdd85d7e4e263e3b66fb41ddc). A mismatch is recorded, not hidden; the run then
    stops unless `--allow-mismatch` is given.

Usage (on the AI station):
  python3 -B camera_transaction_probe.py --url <context-server-url> --repo <navigator repo> --out <dir>
"""
import argparse, base64, hashlib, json, os, platform, statistics, subprocess, sys, time, urllib.request

SESSION_E = dict(route_graph_md5='e0130b78b00ec55822dbc39a41429817', git_commit='f973aa0c4920e47cdd85d7e4e263e3b66fb41ddc',
                 context_server_xplorer_b='<context-server-url>')
N, GAP_S = 50, 1.0

def http_get_json(url, timeout=5):                       # identical to the deployed helper
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

def q(v, p):
    s = sorted(v); k = (len(s) - 1) * p; f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default=SESSION_E['context_server_xplorer_b']); ap.add_argument('--repo')
    ap.add_argument('--out', required=True); ap.add_argument('--allow-mismatch', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=False)
    me = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
    cfg = dict(script_sha256=me, started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), host=platform.node(),
               python=platform.python_version(), url=a.url, n_planned=N, gap_s=GAP_S, session_e_reference=SESSION_E)
    try:
        g = http_get_json(a.url + '/graph', timeout=5)       # same canonicalisation as the deployed _remote_graph_md5()
        cfg['route_graph_md5'] = hashlib.md5(json.dumps(g, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    except Exception as e:
        cfg['route_graph_md5'] = 'ERROR: %r' % e
    if a.repo:
        try: cfg['git_commit'] = subprocess.run(['git', '-C', a.repo, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        except Exception as e: cfg['git_commit'] = 'ERROR: %r' % e
        try: cfg['git_dirty'] = bool(subprocess.run(['git', '-C', a.repo, 'status', '--porcelain'], capture_output=True, text=True).stdout.strip())
        except Exception: cfg['git_dirty'] = None
    cfg['matches_session_e'] = dict(route_graph=cfg['route_graph_md5'] == SESSION_E['route_graph_md5'],
                                    git_commit=(cfg.get('git_commit') == SESSION_E['git_commit']) if a.repo else 'not checked')
    print(json.dumps(cfg, indent=1))
    if (not cfg['matches_session_e']['route_graph'] or cfg['matches_session_e']['git_commit'] is False) and not a.allow_mismatch:
        json.dump(dict(config=cfg, stopped='configuration differs from Session E'), open(os.path.join(a.out, 'CAMERA_PROBE.json'), 'w'), indent=1)
        sys.exit('STOPPED: configuration differs from Session E (see CAMERA_PROBE.json); rerun with --allow-mismatch only by decision')
    rows = []
    for i in range(N):
        t0 = time.perf_counter_ns(); err = None; data = ''
        try:
            cam = http_get_json(f'{a.url}/camera', timeout=10)
            data = cam.get('data', '')
        except Exception as e:
            err = repr(e)[:120]
        t1 = time.perf_counter_ns()
        row = dict(i=i, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), ms=(t1 - t0) / 1e6, error=err, b64_len=len(data))
        if not err:
            try:
                raw = base64.b64decode(data); row.update(jpeg=raw[:2] == b'\xff\xd8', bytes=len(raw), md5=hashlib.md5(raw).hexdigest())
                if i == 0: row['reply_keys'] = sorted(cam.keys())
            except Exception as e:
                row.update(jpeg=False, decode_error=repr(e)[:80])
        row['ok'] = (not err) and bool(data) and row.get('jpeg', False)
        rows.append(row); print('%2d %9.2f ms %s' % (i, row['ms'], 'ok' if row['ok'] else 'FAIL ' + str(err)))
        time.sleep(GAP_S)
    ok = [r['ms'] for r in rows if r['ok']]
    summ = dict(n=len(rows), n_ok=len(ok), n_fail=len(rows) - len(ok), first_ms=rows[0]['ms'],
                median_ms=statistics.median(ok) if ok else None, q1_ms=q(ok, .25) if ok else None, q3_ms=q(ok, .75) if ok else None,
                min_ms=min(ok) if ok else None, max_ms=max(ok) if ok else None,
                distinct_frames=len({r.get('md5') for r in rows if r['ok']}), mean_bytes=statistics.mean([r['bytes'] for r in rows if r['ok']]) if ok else None)
    cfg['ended_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    json.dump(dict(config=cfg, summary=summ, transactions=rows), open(os.path.join(a.out, 'CAMERA_PROBE.json'), 'w'), indent=1)
    print(json.dumps(summ, indent=1))

if __name__ == '__main__':
    main()
