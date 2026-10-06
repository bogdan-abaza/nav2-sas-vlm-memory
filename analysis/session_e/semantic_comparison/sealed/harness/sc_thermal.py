"""GPU thermal/clock logger for the A4 semantic comparison (protocol s.8.5). Separate process, started and checked by sc_harness.py.
Every 5 s: UTC, time.monotonic_ns, and the supported nvidia-smi fields from FIELDS (support is probed once at start and frozen in the
header line; unsupported fields are recorded as unavailable). Stops on SIGTERM.  python3 -B sc_thermal.py <out.csv> [period_s]"""
import sys, os, time, subprocess, signal, json
FIELDS = ['temperature.gpu', 'clocks.sm', 'clocks.mem', 'clocks.max.sm', 'utilization.gpu', 'utilization.memory', 'power.draw', 'power.limit',
          'pstate', 'memory.used', 'clocks_event_reasons.active', 'clocks_throttle_reasons.active', 'clocks_event_reasons.hw_thermal_slowdown',
          'clocks_event_reasons.sw_thermal_slowdown', 'clocks_event_reasons.sw_power_cap']
out, period = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
FAKE = os.environ.get('SC_THERMAL_FAKE') == '1'
def q(fields):
    if FAKE: return ['0'] * len(fields)
    r = subprocess.run(['nvidia-smi', '--query-gpu=' + ','.join(fields), '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=10)
    if r.returncode != 0: raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return [x.strip() for x in r.stdout.strip().splitlines()[0].split(',')]
supported = []
for f in FIELDS:
    try: q([f]); supported.append(f)
    except Exception: pass
stop = [False]
signal.signal(signal.SIGTERM, lambda *a: stop.__setitem__(0, True))
with open(out, 'w', buffering=1) as fh:
    fh.write('# ' + json.dumps(dict(fields_requested=FIELDS, fields_supported=supported, period_s=period, fake=FAKE, started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))) + '\n')
    fh.write(','.join(['utc', 'monotonic_ns'] + supported) + '\n')
    nxt = time.monotonic()
    while not stop[0]:
        try: vals = q(supported) if supported else []
        except Exception as e: vals = ['ERR:' + repr(e)[:60]] * len(supported)
        fh.write(','.join([time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), str(time.monotonic_ns())] + vals) + '\n')
        nxt += period
        while not stop[0] and time.monotonic() < nxt: time.sleep(0.1)
