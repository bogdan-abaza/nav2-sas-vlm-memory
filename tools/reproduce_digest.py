"""
reproduce_digest.py — reproduce digest-ul publicat (MD5 fisier 97241265...)
din log-urile de audit brute, si verifica identitatea de CONTINUT.

Demonstreaza lantul complet:  log-uri brute -> memory_extractor -> digest.

Rulare:
    python3 reproduce_digest.py \
        --logs      ~/Documents/VLM/logs \
        --session-a sprint_73_delivery/session_a/audits \
        --geojson   config/semantic_objects_static.geojson \
        --reference data/memory/memory_digest.json

Iesire: cod 0 daca reproducerea e identica pe continut.
"""
import argparse, glob, json, os, sys, hashlib, datetime

# Setul de intrare al extractorului la momentul compilarii (23 apr 2026, 10:19:36Z):
#   logs/audit_*.jsonl               286 decizii  (7-21 aprilie)
# + session_a/audits/*.jsonl          85 decizii  (22-23 aprilie)
# + archive_session_a_debug/audit_20260423_110739.jsonl   2 decizii
#                                    ---
#                                    373 decizii  == global_stats.total_tasks
EXTRA_DEBUG = ['audit_20260423_110739.jsonl']
CUTOFF_UTC  = '2026-04-23T10:19:36.377832Z'
PLATFORMS   = ['xplorer-b', 'xplorer-c']


def load(paths):
    ents, seen = [], set()
    for f in paths:
        with open(f, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (o.get('_type'), round(o.get('timestamp', 0), 4))
                if key in seen:
                    continue
                seen.add(key)
                ents.append(o)
    return ents


def content_md5(digest):
    """Hash pe CONTINUT, ignorand generated_at (care nu e reproductibil)."""
    body = {k: v for k, v in digest.items() if k != 'generated_at'}
    return hashlib.md5(
        json.dumps(body, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--logs', required=True, help='director cu audit_*.jsonl')
    p.add_argument('--session-a', required=True, help='director cu auditurile sesiunii A')
    p.add_argument('--geojson', required=True)
    p.add_argument('--reference', required=True, help='memory_digest.json de referinta')
    p.add_argument('--extractor', default='.', help='director cu memory_extractor.py')
    a = p.parse_args()
    sys.path.insert(0, os.path.expanduser(a.extractor))
    import memory_extractor as ME

    logs = os.path.expanduser(a.logs)
    paths  = sorted(glob.glob(os.path.join(logs, 'audit_*.jsonl')))
    paths += sorted(glob.glob(os.path.join(os.path.expanduser(a.session_a), '*.jsonl')))
    for name in EXTRA_DEBUG:
        for cand in (os.path.join(logs, 'archive_session_a_debug', name),
                     os.path.join(logs, name)):
            if os.path.exists(cand):
                paths.append(cand)
                break

    ents = load(paths)
    dec, st, _ = ME.split_entries(ents)
    smap = ME.build_session_platform_map(ents)
    ME.tag_entries_with_platform(dec, smap)
    ME.tag_entries_with_platform(st, smap)

    cut = datetime.datetime.fromisoformat(CUTOFF_UTC.replace('Z', '+00:00')).timestamp()
    d = [x for x in dec if x['timestamp'] < cut]
    s = [x for x in st  if x['timestamp'] < cut]

    objs = ME.load_geojson_objects(os.path.expanduser(a.geojson))
    mine = ME.build_digest(
        ME.extract_m1(d, objs, PLATFORMS), ME.extract_m2(d), ME.extract_m3(d),
        ME.extract_m4(s, objs, PLATFORMS), ME.extract_m5(d))

    ref = json.load(open(os.path.expanduser(a.reference), encoding='utf-8'))
    diffs = [k for k in set(ref) | set(mine)
             if k != 'generated_at' and ref.get(k) != mine.get(k)]

    print(f"fisiere citite     : {len(paths)}")
    print(f"decizii sub cutoff : {len(d)}  (asteptat: {ref['global_stats']['total_tasks']})")
    print(f"promovari M3       : {len(mine['l3a_promotions_ready'])}  "
          f"(asteptat: {len(ref['l3a_promotions_ready'])})")
    print(f"content_md5 referinta : {content_md5(ref)}")
    print(f"content_md5 regenerat : {content_md5(mine)}")
    print()
    if diffs:
        print("DIFERENTE:", diffs)
        return 1
    print("REPRODUCERE IDENTICA PE CONTINUT")
    return 0


if __name__ == '__main__':
    sys.exit(main())
