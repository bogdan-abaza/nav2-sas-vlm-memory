#!/usr/bin/env bash
# genereaza_digest_gol.sh — digestul GOL pentru blocul E6, cu extractorul INGHETAT.
#   ./genereaza_digest_gol.sh <cale_src> <cale_config>
#
# ATENTIE: memory_extractor.py NU are flag --empty, iar -o este DIRECTOR, nu fisier.
# Metoda corecta: se da un director de log-uri care contine un singur audit GOL.
# Digestul inghetat nu se atinge.
set -euo pipefail
SRC="${1:?cale src}"; CFG="${2:?cale config}"
TMP="$HOME/digest_gol_build"; DST="$HOME/digest_gol"
rm -rf "$TMP"; mkdir -p "$TMP/logs" "$DST"
: > "$TMP/logs/audit_00000000_000000.jsonl"      # audit gol, dar existent

python3 "$SRC/memory_extractor.py" \
    --logs-dir "$TMP/logs" \
    --geojson  "$CFG/semantic_objects_static_v2.geojson" \
    --output   "$TMP/out"

cp "$TMP/out/memory_digest.json" "$DST/memory_digest.json"

python3 - "$DST/memory_digest.json" <<'PY'
import json,hashlib,sys
p=sys.argv[1]; d=json.load(open(p))
n=len(d.get('l3a_promotions_ready') or [])
b={k:v for k,v in d.items() if k not in ('generated_at','content_md5')}
cm=hashlib.md5(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest()
print()
print('  fisier      :',p)
print('  promovari   :',n,'   (trebuie 0)')
print('  content_md5 :',cm)
print('  md5 fisier  :',hashlib.md5(open(p,'rb').read()).hexdigest())
print()
if n!=0: print('  ESEC: digestul nu e gol.'); raise SystemExit(1)
if cm!='59a7c9cfa25549c9de6ec3c6e0f988d2':
    print('  ATENTIE: content_md5 difera de valoarea prezisa 59a7c9cfa25549c9de6ec3c6e0f988d2')
    print('  Nu blocheaza, dar se consemneaza si se raporteaza inainte de E6.')
else:
    print('  content_md5 coincide cu valoarea prezisa. OK.')
print('  Export inainte de E6:')
print('    export MEMORY_DIGEST_PATH=$HOME/digest_gol/memory_digest.json')
PY
