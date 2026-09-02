#!/usr/bin/env bash
# verifica_start.sh — poarta A1..A4 din fisa zilei 2, intr-o singura rulare.
#   ./verifica_start.sh <cale_src> <cale_config> <cale_maps>
# Iese cu 0 numai daca TOATE trec.
set -uo pipefail
SRC="${1:?cale src}"; CFG="${2:?cale config}"; MAPS="${3:?cale maps}"
rc=0
chk(){ if [ "$2" = "$3" ]; then printf '  OK    %-34s %s\n' "$1" "$2";
       else printf '  ESEC  %-34s\n        obtinut: %s\n        astept: %s\n' "$1" "$2" "$3"; rc=1; fi; }

echo; echo "  === A1 · identitatea codului ==="
chk "git HEAD" "$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null)" "f973aa0"
d="$(git -C "$SRC" status --porcelain 2>/dev/null | wc -l)"
chk "git arbore curat (0 fisiere)" "$d" "0"

echo; echo "  === A3 · hash-uri de configuratie ==="
chk "memory_digest.json"                "$(md5sum "$CFG/memory_digest.json" 2>/dev/null | cut -d' ' -f1)" "97241265217eb4b08e26fb718eb21f40"
chk "semantic_objects_static_v2.geojson" "$(md5sum "$CFG/semantic_objects_static_v2.geojson" 2>/dev/null | cut -d' ' -f1)" "2e48375071c0e4ea7cd38c0e48ef97c5"
chk "route_graph_fiir.geojson"          "$(md5sum "$MAPS/route_graph_fiir.geojson" 2>/dev/null | cut -d' ' -f1)" "440522bc9f0c32997698310f680bfb89"
cm="$(python3 -c "
import json,hashlib,sys
d=json.load(open(sys.argv[1]))
b={k:v for k,v in d.items() if k not in ('generated_at','content_md5')}
print(hashlib.md5(json.dumps(b,sort_keys=True,separators=(',',':')).encode()).hexdigest())" "$CFG/memory_digest.json" 2>/dev/null)"
chk "digest content_md5 (=audit)" "$cm" "0fd61f9e82e8fe6991f0311014384e0c"
np="$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1])).get('l3a_promotions_ready') or []))" "$CFG/memory_digest.json" 2>/dev/null)"
chk "promovari M3 in digest" "$np" "6"

echo; echo "  === A4 · sigiliul E7 ==="
chk "E7_set_sigilat_v2.csv md5" "$(md5sum E7_set_sigilat_v2.csv 2>/dev/null | cut -d' ' -f1)" "1ebb16730b30a1ee8c97f11e6b6f2cdd"
chk "numar instructiuni"        "$(tail -n +2 E7_set_sigilat_v2.csv 2>/dev/null | wc -l)" "28"

echo; echo "  === mediu ==="
printf '  XPLORER_PLATFORM_ID = %s\n' "${XPLORER_PLATFORM_ID:-NESETAT}"
printf '  ROS_DOMAIN_ID       = %s   (trebuie DIFERIT intre B si C)\n' "${ROS_DOMAIN_ID:-NESETAT}"
printf '  MEMORY_DIGEST_PATH  = %s   (trebuie GOL inainte de E3)\n' "${MEMORY_DIGEST_PATH:-<gol, corect>}"
[ -z "${XPLORER_PLATFORM_ID:-}" ] && rc=1

echo
if [ $rc -eq 0 ]; then echo "  TOATE PORTILE TREC. Se poate porni ziua 2."
else echo "  BLOCANT. Nu se porneste pana nu trec toate."; fi
echo
exit $rc
