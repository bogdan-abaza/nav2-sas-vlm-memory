#!/usr/bin/env python3
"""
build_dataset.py — Session E delivery  ->  publishable dataset  data/session_e/

Design rules (do not relax without recording the change in KNOWN_DISCREPANCIES.md):

  R1. FILE CONTENTS ARE NEVER MODIFIED. Every file carried over from the delivery is
      copied byte-for-byte and its MD5 is re-verified after the copy. Romanian text
      inside audits, notes and sealed files is primary evidence and stays verbatim.
  R2. ONLY PATHS ARE TRANSLATED. Directory and file names become English; the mapping
      is fully recorded in PROVENANCE.tsv so any renamed file can be traced back.
  R3. ENGLISH IS ADDED, NOT SUBSTITUTED. Machine-readable English indexes
      (missions.csv, sessions.csv) are generated *alongside* the raw evidence.
  R4. NOTHING IS DROPPED. Duplicates and conflicting copies are both carried over
      under distinct names and documented, never silently reconciled.

Usage:  python3 build_dataset.py --source <delivery_root> --output <dataset_root>
"""

import argparse, csv, hashlib, json, os, re, shutil, sys, time, zipfile
from collections import Counter, OrderedDict
from datetime import datetime, timezone

# --------------------------------------------------------------------------------------
# Path mapping.  key = path relative to the delivery root, value = path in the dataset.
# A trailing '/' means "directory: map the name, recurse with the same rules".
# Anything not listed keeps its original name (already English or language-neutral).
# --------------------------------------------------------------------------------------

DIR_MAP = {
    'note':                 'notes',
    'ziua1_20260820':       'day1_20260820',
    'ziua2_20260821':       'day2_20260821',
    'cod':                  'code',
    'dyn_arhiva':           'dynamic_graph_archive',
    'dovezi':               'evidence',
    'memorie':              'memory',
    'arhiva':               'archive',
    'digest_gol':           'digest_empty',
    'sesiune':              'session',
}

FILE_MAP = {
    'MANIFEST.txt':                                   '_source/MANIFEST_ro.txt',
    'MD5SUMS_TOTAL.txt':                              '_source/MD5SUMS_TOTAL.txt',
    'Terminale Xplorer B-C.txt':                      '_source/terminals_xplorer_b_c_ro.txt',

    'note/NOTE_ziua1_20260820.md':                    'notes/session_notes_day1_20260820_ro.md',
    'note/NOTE_ziua2_20260821.md':                    'notes/session_notes_day2_20260821_ro.md',
    'ziua1_20260820/NOTE_ziua1_20260820.md':          'day1_20260820/session_notes_day1_ro.md',

    'ziua1_20260820/INDEX_misiuni.txt':               'day1_20260820/mission_index_ro.txt',
    'ziua2_20260821/INDEX_misiuni.txt':               'day2_20260821/mission_index_ro.txt',
    'ziua1_20260820/MD5SUMS.txt':                     'day1_20260820/CHECKSUMS_source.md5',
    'ziua2_20260821/MD5SUMS.txt':                     'day2_20260821/CHECKSUMS_source.md5',
    'ziua2_20260821/SIGILIU_E7.txt':                  'day2_20260821/E7_seal.txt',

    'ziua2_20260821/config/digest_hashes_ziua2.txt':  'day2_20260821/config/digest_hashes_day2.txt',
    'ziua2_20260821/config/memory_digest_ACTIV_la_sfarsitul_zilei.json':
        'day2_20260821/config/memory_digest_active_end_of_day.json',

    'ziua2_20260821/memorie/arhiva/memory_digest_INGHETAT_20260821.json':
        'day2_20260821/memory/archive/memory_digest_frozen_20260821.json',
    'ziua2_20260821/memorie/arhiva/memory_digest_inainte_E4b_1730.json':
        'day2_20260821/memory/archive/memory_digest_before_E4b_1730.json',

    'ziua2_20260821/sesiune/Decizii_declarate_inainte_de_ziua2.md':
        'day2_20260821/session/declared_decisions_before_day2_ro.md',
    'ziua2_20260821/sesiune/E7_instructiuni_de_publicat.txt':
        'day2_20260821/session/E7_instructions_to_publish.txt',
    'ziua2_20260821/sesiune/E7_protocol_sigilare.md':
        'day2_20260821/session/E7_sealing_protocol_ro.md',
    'ziua2_20260821/sesiune/E7_set_sigilat_v2.csv':
        'day2_20260821/session/E7_sealed_set_v2.csv',
    'ziua2_20260821/sesiune/E_Fise_rulaj_ZIUA2.html':
        'day2_20260821/session/E_run_sheets_day2_ro.html',
    'ziua2_20260821/sesiune/blocuri.env':
        'day2_20260821/session/blocks.env',
    'ziua2_20260821/sesiune/digest_hashes_CORECTAT.txt':
        'day2_20260821/session/digest_hashes_corrected.txt',
    'ziua2_20260821/sesiune/genereaza_digest_gol.sh':
        'day2_20260821/session/generate_empty_digest.sh',
    'ziua2_20260821/sesiune/verifica_start.sh':
        'day2_20260821/session/verify_start.sh',
}

# Files whose MD5 is quoted in the paper / seals and must never change.
SEALED = {
    'day2_20260821/session/E7_sealed_set_v2.csv': '1ebb16730b30a1ee8c97f11e6b6f2cdd',
    'day1_20260820/config/route_graph_fiir.geojson': '440522bc9f0c32997698310f680bfb89',
    'day2_20260821/config/route_graph_fiir.geojson': '440522bc9f0c32997698310f680bfb89',
}

# Files that exist in the working folder on the author's disk but are NOT inside the
# delivered archive. They are carried into the dataset under _outside_delivery/ so that
# nothing is lost, but they are never treated as peers of delivered evidence.
OUTSIDE_DELIVERY = {
    'Terminale Xplorer B-C.txt':
        '_outside_delivery/terminals_xplorer_b_c_ro.txt',
    'ziua2_20260821/NOTE_ziua2_20260821.md':
        '_outside_delivery/session_notes_day2_ro_superseded_draft.md',
}

DAYS = OrderedDict([('day1_20260820', 'ziua1_20260820'), ('day2_20260821', 'ziua2_20260821')])


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def map_rel(rel):
    """Map a delivery-relative path to its dataset-relative path."""
    rel = rel.replace(os.sep, '/')
    if rel in FILE_MAP:
        return FILE_MAP[rel]
    parts = rel.split('/')
    return '/'.join(DIR_MAP.get(p, p) for p in parts)


# --------------------------------------------------------------------------------------
# Source reader — the delivered .zip is the authority; a directory is accepted as a
# fallback but cannot carry the original file timestamps.
# --------------------------------------------------------------------------------------

class SourceReader:
    """Yields (rel_path, size, mtime_iso, open_fn) for every file in the delivery."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.is_zip = zipfile.is_zipfile(self.path) and not os.path.isdir(self.path)
        if self.is_zip:
            self.zf = zipfile.ZipFile(self.path)
            self.archive_md5 = md5(self.path)
            names = [i for i in self.zf.infolist() if not i.is_dir()]
            prefix = os.path.commonprefix([i.filename for i in names])
            self.prefix = prefix[:prefix.rfind('/') + 1] if '/' in prefix else ''
            self.entries = names
        else:
            self.zf = None
            self.archive_md5 = None

    @property
    def kind(self):
        return 'archive' if self.is_zip else 'directory'

    def __iter__(self):
        if self.is_zip:
            for i in sorted(self.entries, key=lambda e: e.filename):
                rel = i.filename[len(self.prefix):]
                y, mo, d, h, mi, se = i.date_time
                iso_t = f'{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{se:02d}'
                yield rel, i.file_size, iso_t, (lambda e=i: self.zf.open(e))
        else:
            for dirpath, dirnames, filenames in os.walk(self.path):
                dirnames.sort()
                for name in sorted(filenames):
                    full = os.path.join(dirpath, name)
                    rel = os.path.relpath(full, self.path).replace(os.sep, '/')
                    st = os.stat(full)
                    iso_t = datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%dT%H:%M:%S')
                    yield rel, st.st_size, iso_t, (lambda f=full: open(f, 'rb'))


# --------------------------------------------------------------------------------------
# Stage 1 — copy every file, byte-for-byte, verifying the MD5 on both sides.
# --------------------------------------------------------------------------------------

def set_mtime(path, mtime_iso):
    """Stamp the destination with the source's modification time, best effort."""
    try:
        ts = datetime.strptime(mtime_iso, '%Y-%m-%dT%H:%M:%S').timestamp()
        if abs(os.stat(path).st_mtime - ts) > 1.5:
            os.utime(path, (ts, ts))
    except Exception:
        pass


def copy_tree(reader, dst_root, deadline=None):
    """Copy every delivered file, verifying MD5 on both sides.

    Idempotent: a destination file that already carries the correct MD5 is left alone,
    so the build can be re-run over an existing tree and can be resumed after an
    interruption without ever deleting anything. If `deadline` (a monotonic seconds
    value) is given, the copy stops cleanly when it is reached and reports the
    remaining work instead of running to completion.
    """
    rows, errors = [], []
    remaining = 0
    for rel, size, mtime_iso, opener in reader:
        outside = rel in OUTSIDE_DELIVERY
        dst_rel = OUTSIDE_DELIVERY[rel] if outside else map_rel(rel)
        dst = os.path.join(dst_root, dst_rel)

        h = hashlib.md5()
        with opener() as fh:
            for b in iter(lambda: fh.read(1 << 20), b''):
                h.update(b)
        src_md5 = h.hexdigest()

        if os.path.exists(dst) and os.path.getsize(dst) == size and md5(dst) == src_md5:
            dst_md5 = src_md5                          # already correct, nothing to re-copy
            set_mtime(dst, mtime_iso)                  # but always re-assert the timestamp
        elif deadline is not None and time.monotonic() > deadline:
            remaining += 1
            continue
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with opener() as fin, open(dst, 'wb') as fout:
                shutil.copyfileobj(fin, fout, 1 << 20)
            dst_md5 = md5(dst)
            set_mtime(dst, mtime_iso)

        if src_md5 != dst_md5:
            errors.append(f'MD5 mismatch after copy: {rel} -> {dst_rel}')
        if dst_rel in SEALED and dst_md5 != SEALED[dst_rel]:
            errors.append(f'SEALED FILE MD5 CHANGED: {dst_rel} '
                          f'expected {SEALED[dst_rel]} got {dst_md5}')
        rows.append(OrderedDict([
            ('dataset_path', dst_rel),
            ('source_path', rel),
            ('source_mtime', mtime_iso),
            ('bytes', size),
            ('md5', dst_md5),
            ('renamed', 'yes' if dst_rel != rel else 'no'),
            ('content_modified', 'no'),
            ('sealed', 'yes' if dst_rel in SEALED else 'no'),
            ('in_delivered_archive', 'no' if outside else 'yes'),
        ]))
    return rows, errors, remaining


# --------------------------------------------------------------------------------------
# Stage 2 — generate the English machine-readable indexes from the audit logs.
# --------------------------------------------------------------------------------------

MISSION_COLUMNS = [
    'day', 'run_id', 'audit_file', 'platform_id', 'record_seq', 'timestamp_utc',
    'experiment_id', 'experiment_phase', 'semantic_intent_id', 'repetition_index',
    'mission_index', 'concurrency_group_id', 'concurrent_peers',
    'instruction_text', 'instruction_language',
    'resolution_method', 'resolution_step', 'is_escalated',
    'escalation_reason', 'negation_intent', 'negation_markers',
    'm3_jaccard_score', 'm3_runner_up_score', 'm3_matched_example',
    'vlm_eval_count', 'vlm_raw_reason', 'vlm_error',
    'node_id', 'node_name', 'expected_node_id',
    'nav_outcome', 'arrival_ok', 'xy_error_m', 'distance_traveled_m',
    'start_x_m', 'start_y_m', 'start_yaw_rad', 'end_x_m', 'end_y_m', 'end_yaw_rad',
    'amcl_converged', 'amcl_covariance_trace',
    'resolve_ms', 'vlm_ms', 'nav_total_s', 'reroute_count', 'blocked_attempts',
    'validation_allowed', 'validation_reason',
    'confirmation_method', 'confirmation_signature_type', 'confirmed',
    'confirmation_confidence', 'confirmation_parse_status', 'confirmation_prompt_md5',
    'm3_promotion_triggered', 'm3_preferences_count',
    'memory_status', 'digest_content_md5', 'digest_generated_at',
    'memory_prefix_included', 'memory_prefix_chars',
    'luminance_mean',
    'image_start', 'image_start_md5', 'image_finish', 'image_finish_md5',
]

SESSION_COLUMNS = [
    'day', 'run_id', 'audit_file', 'platform_id', 'version', 'git_commit', 'git_dirty',
    'experiment_id', 'experiment_phase', 'protocol_version', 'audit_schema_version',
    'vlm_model', 'vlm_model_digest', 'vlm_quantization', 'ollama_version',
    'gpu_driver_version', 'sas_text_version',
    'm3_jaccard_threshold', 'm3_abstention_margin',
    'geojson_md5', 'route_graph_md5', 'route_graph_source',
    'memory_digest_path', 'memory_status', 'memory_loaded', 'memory_digest_hash',
    'memory_digest_size_bytes', 'm3_preferences_count',
    'poi_signatures_loaded', 'pose_based_radius_m',
    'odom_topic', 'yolo_dedup_radius_m', 'yolo_min_observations',
    'context_server', 'context_server_url', 'policy_path', 'platform_profile',
    'decision_records',
]

# Romanian markers used only to tag instruction_language; the text itself is untouched.
RO_MARKERS = re.compile(
    r'\b(du[- ]?m[ăa]|vreau|unde|este|sunt|caut|toalet[ăa]|sal[ăa]|scaun|apa|ap[ăa]|'
    r'nu\b|la\b|m[âa]inile|odihn|obosit|intrare|ie[sș]ire|cl[ăa]dire|te rog)\b', re.I)


def _get(d, *path, default=''):
    cur = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def iso(ts):
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(timespec='milliseconds')
    except Exception:
        return ''


def build_indexes(src_root):
    # src_root here is the *built dataset* root: indexes are derived from published files
    missions, sessions, stats = [], [], Counter()
    for day, src_day in DAYS.items():
        logs = os.path.join(src_root, day, 'logs')
        for audit in sorted(f for f in os.listdir(logs) if f.startswith('audit_') and f.endswith('.jsonl')):
            start, startup, decisions = {}, {}, []
            with open(os.path.join(logs, audit), encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    t = rec.get('_type')
                    if t == 'session_start':
                        start = rec
                    elif t == 'navigator_startup':
                        startup = rec
                    elif t == 'decision':
                        decisions.append(rec)

            run_id = start.get('session_id') or startup.get('run_id') or audit[6:-6]
            platform = start.get('platform_id') or startup.get('platform_id') or ''

            s = OrderedDict((c, '') for c in SESSION_COLUMNS)
            s.update(day=day, run_id=run_id, audit_file=f'{day}/logs/{audit}',
                     platform_id=platform, decision_records=len(decisions))
            for c in SESSION_COLUMNS:
                if c in startup and startup[c] is not None:
                    s[c] = startup[c]
            s['audit_schema_version'] = startup.get('audit_schema_version') or startup.get('audit_schema') or ''
            sessions.append(s)

            for rec in decisions:
                ex = rec.get('extra') or {}
                cf = rec.get('confirmation') or {}
                tm = rec.get('timing') or {}
                vd = rec.get('validation') or {}
                im = rec.get('images') or {}
                sp = ex.get('start_pose') or [None, None, None]
                ep = ex.get('end_pose') or [None, None, None]
                _mi = ex.get('m3_match_info') if isinstance(ex.get('m3_match_info'), dict) else {}
                _vr = rec.get('vlm_response') if isinstance(rec.get('vlm_response'), dict) else {}
                instr = rec.get('instruction') or ''
                method = rec.get('resolution_method') or ''

                m = OrderedDict((c, '') for c in MISSION_COLUMNS)
                m.update(
                    day=day, run_id=ex.get('run_id') or run_id,
                    audit_file=f'{day}/logs/{audit}',
                    platform_id=rec.get('platform_id') or platform,
                    record_seq=rec.get('_seq', ''),
                    timestamp_utc=iso(rec.get('timestamp')),
                    experiment_id=ex.get('experiment_id', ''),
                    experiment_phase=ex.get('experiment_phase', ''),
                    semantic_intent_id=ex.get('semantic_intent_id', ''),
                    repetition_index=ex.get('repetition_index', ''),
                    mission_index=ex.get('mission_index', ''),
                    concurrency_group_id=ex.get('concurrency_group_id', ''),
                    concurrent_peers=ex.get('concurrent_peers', ''),
                    instruction_text=instr,
                    instruction_language='ro' if RO_MARKERS.search(instr) else 'en',
                    resolution_method=method,
                    resolution_step=ex.get('resolution_step', ''),
                    is_escalated='yes' if method == 'escalated' else 'no',
                    escalation_reason=ex.get('escalation_reason', ''),
                    negation_intent=ex.get('negation_intent', ''),
                    negation_markers='|'.join(ex.get('negation_markers') or []),
                    m3_jaccard_score=_mi.get('jaccard_score', ''),
                    m3_runner_up_score=_mi.get('runner_up', ''),
                    m3_matched_example=_mi.get('matched_example', ''),
                    vlm_eval_count=_vr.get('eval_count', ''),
                    vlm_raw_reason=(_vr.get('raw_reason') or '')[:200],
                    vlm_error=str(ex.get('vlm_error') or '')[:200],
                    node_id=rec.get('node_id', ''), node_name=rec.get('node_name', ''),
                    expected_node_id=ex.get('expected_node_id', ''),
                    nav_outcome=rec.get('nav_outcome', ''),
                    arrival_ok=ex.get('arrival_ok', ''),
                    xy_error_m=ex.get('xy_error_m', ''),
                    distance_traveled_m=ex.get('distance_traveled_m', ''),
                    start_x_m=sp[0], start_y_m=sp[1], start_yaw_rad=sp[2],
                    end_x_m=ep[0], end_y_m=ep[1], end_yaw_rad=ep[2],
                    amcl_converged=ex.get('amcl_converged', ''),
                    amcl_covariance_trace=ex.get('amcl_covariance_trace', ''),
                    resolve_ms=tm.get('resolve_ms', ''), vlm_ms=tm.get('vlm_ms', ''),
                    nav_total_s=tm.get('nav_total_s', ''),
                    reroute_count=rec.get('reroute_count', ''),
                    blocked_attempts=rec.get('blocked_attempts', ''),
                    validation_allowed=vd.get('allowed', ''),
                    validation_reason=vd.get('reason', ''),
                    confirmation_method=cf.get('confirmation_method', ''),
                    confirmation_signature_type=cf.get('signature_type', ''),
                    confirmed=cf.get('confirmed', ''),
                    confirmation_confidence=cf.get('confidence', ''),
                    confirmation_parse_status=cf.get('parse_status', ''),
                    confirmation_prompt_md5=cf.get('confirmation_prompt_md5', ''),
                    m3_promotion_triggered=ex.get('m3_promotion_triggered', ''),
                    m3_preferences_count=ex.get('m3_preferences_count', ''),
                    memory_status=startup.get('memory_status', ''),
                    digest_content_md5=ex.get('digest_content_md5', ''),
                    digest_generated_at=ex.get('digest_generated_at', ''),
                    memory_prefix_included=ex.get('memory_prefix_included', ''),
                    memory_prefix_chars=ex.get('memory_prefix_chars', ''),
                    luminance_mean=ex.get('luminance_mean', ''),
                    image_start=f'{day}/logs/{im["start"]}' if im.get('start') else '',
                    image_start_md5=im.get('start_md5', ''),
                    image_finish=f'{day}/logs/{im["finish"]}' if im.get('finish') else '',
                    image_finish_md5=im.get('finish_md5', ''),
                )
                missions.append(m)
                stats[(day, 'method', method)] += 1
                stats[(day, 'total', 'records')] += 1
    return missions, sessions, stats


def write_csv(path, columns, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)


# --------------------------------------------------------------------------------------
# Stage 3 — verify every image referenced by an audit is present with the recorded MD5.
# --------------------------------------------------------------------------------------

def verify_images(dst_root, missions):
    present = missing = mismatch = 0
    problems = []
    for m in missions:
        for pk, hk in (('image_start', 'image_start_md5'), ('image_finish', 'image_finish_md5')):
            rel = m[pk]
            if not rel:
                continue
            path = os.path.join(dst_root, rel)
            if not os.path.exists(path):
                missing += 1
                problems.append(f'MISSING {rel}')
                continue
            present += 1
            if m[hk] and md5(path) != m[hk]:
                mismatch += 1
                problems.append(f'MD5 MISMATCH {rel}')
    return present, missing, mismatch, problems


# --------------------------------------------------------------------------------------

README = """# Session E — raw dataset

Two experimental days, 20 and 21 August 2026, on the FIIR indoor test floor, with the
two-platform SAS stack (`xplorer-b`, `xplorer-c`). This directory is the *raw evidence*
for the Session E experiments (blocks E0–E7, E4b) plus generated English indexes.

## What is and is not modified

Every file carried over from the delivery is **byte-identical** to the original. Only
directory and file *names* were translated to English. `PROVENANCE.tsv` maps every file
in this dataset back to its original path and records its MD5, so any rename is
reversible and any file is verifiable.

Romanian text inside the audit logs, the session notes and the sealed instruction set is
**primary evidence and was not translated**. Translating it would destroy the record of
what was actually said to the robot. English access to the same content is provided by
the generated indexes below, which add columns rather than replacing text.

## Generated indexes (English, machine-readable)

| File | Rows | Content |
|---|---|---|
| `missions.csv` | one per decision record | full flattened decision: instruction, resolution path, node, navigation outcome, poses, AMCL state, timings, visual confirmation, memory state, image references |
| `sessions.csv` | one per audit file | run configuration: platform, model, digest, thresholds, graph hashes, code commit |
| `PROVENANCE.tsv` | one per file | dataset path, source path, size, MD5, renamed/sealed flags |
| `CHECKSUMS.md5` | one per file | MD5 of every file as published |

`external_reference/` is produced by `apriltag_reference.py` and `analysis/` by
`analyze_session_e.py`; each carries its own `CHECKSUMS.md5`. This build neither writes
nor verifies them.

`analysis/results_E.json` is the single source of every figure quoted in the response to
reviewers, keyed by reviewer point. Nothing in that letter should be typed by hand.

Both CSVs are generated by `build_dataset.py` directly from the `.jsonl` audit logs. They
contain no hand-entered values.

## Counting convention — read before quoting any n

An audit record with `resolution_method = "escalated"` is an **L3b attempt that failed to
return parseable JSON**. It is a record of an attempt, not of a completed decision.

* `missions.csv` contains **all** records, including escalated ones.
* Filter `is_escalated = "no"` to reproduce the "decision lines" count used in the
  delivery manifest.

Both conventions are legitimate; mixing them is not. `KNOWN_DISCREPANCIES.md` documents
where the source documents mix them.

## Verifying this dataset

```
md5sum -c CHECKSUMS.md5
python3 build_dataset.py --source <delivery> --output <dataset> --verify-only
```

## Layout

```
_source/                      delivery-level manifest and checksums, kept verbatim
notes/                        session notes as written during the runs (Romanian)
day1_20260820/
  code/                       frozen source at the commit used for the runs
  config/                     route graph, static semantic objects, memory digest
  dynamic_graph_archive/      per-run snapshots of the dynamic graph
  logs/                       audit_<run>.jsonl  +  <run>/mission_<n>_<node>/*.jpg
day2_20260821/
  ... same, plus:
  evidence/                   raw VLM payload/response captures
  memory/                     digests and per-block extractor outputs
  session/                    run sheets, sealed E7 set, start-gate scripts
```

`code/` and `config/` are byte-identical between the two days; both copies are kept so
each day verifies standalone against its own `CHECKSUMS_source.md5`.
"""


# --------------------------------------------------------------------------------------
# Stage 4b — known discrepancies, computed from the data rather than asserted.
# --------------------------------------------------------------------------------------

def source_block(reader, prov):
    lines = ['# Source of this dataset\n']
    if reader.archive_md5:
        lines += [
            'This dataset was built from the delivery archive as received, not from an',
            'unpacked working copy. The archive is the provenance root:\n',
            '```',
            f'file : {os.path.basename(reader.path)}',
            f'md5  : {reader.archive_md5}',
            f'files: {len(reader.entries)}',
            '```\n',
            'Building from the archive matters for two reasons. It fixes exactly which files',
            'were delivered, so a file that later appeared in the working folder cannot be',
            'promoted to evidence by accident. And it preserves the original modification',
            'time of every file, which an unpack-and-copy loses.\n',
        ]
    else:
        lines += ['Built from an unpacked directory. Original file timestamps are those of',
                  'the local filesystem and may reflect extraction, not creation.\n']

    dated = sorted((r['source_mtime'], r['dataset_path'])
                   for r in prov if r.get('source_mtime'))
    if dated:
        months = Counter(t[:7] for t, _ in dated)
        lines += [
            '## File timestamps\n',
            '`PROVENANCE.tsv` carries a `source_mtime` column for every file, taken from the',
            'archive rather than from the filesystem, so it survives copying, cloning and',
            'checkout. Times are local (Europe/Bucharest, UTC+3 in August 2026) with the',
            '2-second resolution of the archive format, and carry no timezone of their own.\n',
            'Spot check against file content: `day1_20260820/logs/audit_20260820_115934.jsonl`',
            'and the `timestamp_utc` of its first decision record differ by exactly 3 hours,',
            'which is the expected offset.\n',
            '### Files per month\n',
            '| month | files |', '|---|---|',
        ]
        for m in sorted(months):
            lines.append(f'| {m} | {months[m]} |')
        lines += ['', '### The twelve oldest files\n',
                  'These bound how far back the delivered material reaches:\n',
                  '| source_mtime | dataset path |', '|---|---|']
        for t, path in dated[:12]:
            lines.append(f'| {t} | `{path}` |')
        lines += ['', f'The most recent file is `{dated[-1][1]}` at {dated[-1][0]}.\n']

    outside = [r for r in prov if r.get('in_delivered_archive') == 'no']
    if outside:
        lines += ['## Files outside the delivered archive\n',
                  'These exist in the working folder but not in the archive. They are kept',
                  'under `_outside_delivery/` and are not evidence of what was run:\n',
                  '| dataset path | source path | md5 |', '|---|---|---|']
        for r in outside:
            lines.append(f"| `{r['dataset_path']}` | `{r['source_path']}` | `{r['md5']}` |")
        lines.append('')
    return '\n'.join(lines) + '\n'


def known_discrepancies(dst_root, missions, reader=None):
    by_day = {}
    for day in DAYS:
        rows = [m for m in missions if m['day'] == day]
        meth = Counter(m['resolution_method'] for m in rows)
        esc = meth.get('escalated', 0)
        neg = meth.get('L3b_vlm_negation_blocked', 0)
        ok = meth.get('L3b_vlm', 0)
        by_day[day] = dict(total=len(rows), esc=esc, neg=neg, ok=ok, meth=meth)

    # orphan images: present on disk but referenced by no audit record
    referenced = {m[k] for m in missions for k in ('image_start', 'image_finish') if m[k]}
    on_disk = set()
    for day in DAYS:
        base = os.path.join(dst_root, day, 'logs')
        for dirpath, _, files in os.walk(base):
            for f in files:
                if f.endswith('.jpg'):
                    on_disk.add(os.path.relpath(os.path.join(dirpath, f), dst_root).replace(os.sep, '/'))
    orphans = sorted(on_disk - referenced)

    def note(day, rel):
        p = os.path.join(dst_root, rel)
        return md5(p) if os.path.exists(p) else '(absent)'

    d1, d2 = by_day['day1_20260820'], by_day['day2_20260821']
    lines = []
    A = lines.append

    A('# Known discrepancies in the Session E source documents\n')
    A('Every item below is a conflict **between source documents**, carried into this dataset')
    A('unresolved on purpose. Nothing was edited to make the sources agree. Each item states')
    A('which value the audit logs support, and shows the arithmetic so the reader can check it.\n')

    A('## D-1 · A superseded copy of the day-2 session notes\n')
    A('The delivered archive contains **one** day-2 note, at `notes/`. The working folder on')
    A('the author machine contained a second copy at `ziua2_20260821/`, same byte length, with')
    A('**one differing line**:\n')
    A('* delivered  (`notes/session_notes_day2_20260821_ro.md`): *"10 esecuri din 63 de apeluri L3b, 15.9%"*')
    A('* not delivered (`_outside_delivery/session_notes_day2_ro_superseded_draft.md`): *"... din 51 ... 19.6%"*\n')
    A('The delivered figure is the correct one. From `missions.csv`, day 2:\n')
    A('```')
    A(f'resolution_method == "L3b_vlm"    {d2["ok"]:>4}   L3b calls that returned parseable JSON')
    A(f'resolution_method == "escalated"  {d2["esc"]:>4}   L3b calls that did not')
    A( '                                  ----')
    A(f'total L3b calls                   {d2["ok"] + d2["esc"]:>4}   failure rate '
      f'{d2["esc"]}/{d2["ok"] + d2["esc"]} = {100.0 * d2["esc"] / max(1, d2["ok"] + d2["esc"]):.1f}%')
    A('```\n')
    A('The denominator 51 cannot be reconstructed from any field in the logs. The draft is')
    A('kept under `_outside_delivery/` so the discrepancy stays auditable, but it carries no')
    A('evidential weight: it was never part of the delivery.\n')

    A('## D-2 · Three different denominators for the L3b failure rate\n')
    A('The source documents use three incompatible conventions. They differ in whether')
    A('negation-blocked calls count as L3b calls:\n')
    A('| document | day | quoted | denominator is |')
    A('|---|---|---|---|')
    A(f'| `_source/MANIFEST_ro.txt` | 1 | 4 / 42 = 9.5% | `L3b_vlm` + `L3b_vlm_negation_blocked` + `escalated` = '
      f'{d1["ok"]} + {d1["neg"]} + {d1["esc"]} |')
    A(f'| session notes | 1 | 4 / 20 = 20% | `L3b_vlm` + `escalated` = {d1["ok"]} + {d1["esc"]} |')
    A(f'| session notes rev B | 2 | 10 / 63 = 15.9% | `L3b_vlm` + `escalated` = {d2["ok"]} + {d2["esc"]} |')
    A(f'| session notes rev A | 2 | 10 / 51 = 19.6% | not reconstructible |')
    A('')
    A(f'Day 2 has **zero** `L3b_vlm_negation_blocked` records ({d2["neg"]}), so on day 2 the first')
    A('two conventions coincide. On day 1 they do not, which is why the same day is reported')
    A('both as 9.5% and as 20%.\n')
    A('**Recommended convention for the paper**, applied identically to both days:')
    A('`L3b_vlm + escalated`, i.e. calls that were issued and either parsed or did not.')
    A('A negation-blocked call is a guard decision, not an L3b outcome. Under that convention:\n')
    A('```')
    A(f'day 1  {d1["esc"]} / {d1["ok"] + d1["esc"]} = {100.0 * d1["esc"] / max(1, d1["ok"] + d1["esc"]):.1f}%')
    A(f'day 2  {d2["esc"]} / {d2["ok"] + d2["esc"]} = {100.0 * d2["esc"] / max(1, d2["ok"] + d2["esc"]):.1f}%')
    A('```\n')
    A('Whichever convention is chosen, it must be stated and used for both days.\n')

    A('## D-3 · Record count vs decision count\n')
    A('`_source/MANIFEST_ro.txt` reports 89 and 123 "linii de decizie". `missions.csv` has')
    A(f'{d1["total"]} and {d2["total"]} rows. The difference is exactly the `escalated` records')
    A(f'({d1["esc"]} and {d2["esc"]}), which the manifest excludes:\n')
    A('```')
    for day, d in by_day.items():
        A(f'{day}: {d["total"]} rows - {d["esc"]} escalated = {d["total"] - d["esc"]} decision lines')
    A('```\n')
    A('Filter `is_escalated = "no"` in `missions.csv` to reproduce the manifest figure.\n')

    A('## D-4 · Superseded `content_md5` in the day-1 configuration\n')
    A('`day1_20260820/config/digest_hashes.txt` records')
    A('`content_md5 = bdc89fcf1e17f8c577a941cd80be70ab`, labelled "cel din audit" ("the one from')
    A('the audit"). The label is wrong: the day-1 audits record')
    A('`digest_content_md5 = 0fd61f9e82e8fe6991f0311014384e0c` in every record. The error was')
    A('caught by the start-gate script on 21 August and corrected in')
    A('`day2_20260821/session/digest_hashes_corrected.txt`, which is the file to cite. The')
    A('original is kept because it is what the day-1 runs were configured against.\n')

    A('## D-5 · Images from aborted runs\n')
    A(f'{len(orphans)} images are present on disk but referenced by no audit record. They belong to')
    A('runs that were started and abandoned before a decision was written:\n')
    for o in orphans:
        A(f'* `{o}`')
    A('')
    A('They are kept for completeness and should be excluded from any per-mission analysis;')
    A('`missions.csv` already excludes them, since it lists only images an audit record references.\n')

    A('## D-6 · AprilTag id1 — surveyed pose inconsistent with its optical geometry\n')
    A('Recorded here because it constrains what the external-localization analysis may use.')
    A('Across four arrivals near `plant_3`, on both days, tag id1 places the camera at')
    A('0.331 m +/- 0.012 m above the floor. The camera on `xplorer-c` is at 0.170 m, and the same')
    A('platform against tag id3 returns 0.126-0.171 m. No tag height or rotation about the')
    A('vertical closes the geometry; matching the camera height would require the tag centre at')
    A('-0.08 m, below the floor. The tag is therefore not mounted as surveyed, and its four')
    A('samples are excluded from the external-reference aggregate. See')
    A('`external_reference/README.md`.\n')

    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--verify-only', action='store_true')
    ap.add_argument('--extra-dir', default=None,
                    help='working folder holding files that are NOT in the delivered '
                         'archive; only names listed in OUTSIDE_DELIVERY are taken, and '
                         'they land under _outside_delivery/')
    ap.add_argument('--time-budget', type=float, default=0,
                    help='seconds; stop the copy stage cleanly when reached and exit 10 '
                         'so the build can be resumed in short steps')
    args = ap.parse_args()

    src = os.path.abspath(args.source)
    dst = os.path.abspath(args.output)
    reader = SourceReader(src)
    print(f'source : {src}  ({reader.kind})')
    if reader.archive_md5:
        print(f'         archive md5 {reader.archive_md5}')
    print(f'output : {dst}\n')
    if reader.is_zip and args.extra_dir:
        extra = SourceReader(os.path.abspath(args.extra_dir))
        print(f'extra  : {args.extra_dir} (files outside the archive)\n')
    else:
        extra = None

    if not args.verify_only:
        os.makedirs(dst, exist_ok=True)
        deadline = time.monotonic() + args.time_budget if args.time_budget else None
        print('[1/5] copying and verifying files ...')
        prov, errors, remaining = copy_tree(reader, dst, deadline)
        if extra is not None and not remaining:
            keep = [(r, sz, mt, op) for r, sz, mt, op in extra if r in OUTSIDE_DELIVERY]
            if keep:
                p2, e2, _ = copy_tree(iter(keep), dst, None)
                prov += p2
                errors += e2
        print(f'      {len(prov)} files in place, {len(errors)} integrity errors')
        for e in errors:
            print('      !! ' + e)
        if errors:
            sys.exit('ABORT: integrity errors during copy')
        if remaining:
            print(f'\nTIME BUDGET REACHED — {remaining} files still to copy.')
            print('Re-run the same command to resume; files already correct are skipped.')
            sys.exit(10)
    else:
        prov, errors = [], []

    print('[2/5] building English indexes from audit logs ...')
    missions, sessions, stats = build_indexes(dst)
    write_csv(os.path.join(dst, 'missions.csv'), MISSION_COLUMNS, missions)
    write_csv(os.path.join(dst, 'sessions.csv'), SESSION_COLUMNS, sessions)
    print(f'      missions.csv : {len(missions)} records')
    print(f'      sessions.csv : {len(sessions)} runs')

    print('[3/5] verifying every referenced image is present with the recorded MD5 ...')
    present, missing, mismatch, problems = verify_images(dst, missions)
    print(f'      referenced images present {present}, missing {missing}, md5 mismatch {mismatch}')
    for p in problems[:20]:
        print('      !! ' + p)

    print('[4/5] writing README and provenance ...')
    with open(os.path.join(dst, 'README.md'), 'w', encoding='utf-8') as fh:
        fh.write(README)
    with open(os.path.join(dst, 'KNOWN_DISCREPANCIES.md'), 'w', encoding='utf-8') as fh:
        fh.write(known_discrepancies(dst, missions, reader))
    with open(os.path.join(dst, 'SOURCE.md'), 'w', encoding='utf-8') as fh:
        fh.write(source_block(reader, prov))
    if prov:
        prov.sort(key=lambda r: r['dataset_path'])
        for extra in ('missions.csv', 'sessions.csv', 'README.md',
                      'KNOWN_DISCREPANCIES.md', 'SOURCE.md'):
            p = os.path.join(dst, extra)
            prov.append(OrderedDict([('dataset_path', extra), ('source_path', '(generated)'),
                                     ('bytes', os.path.getsize(p)), ('md5', md5(p)),
                                     ('renamed', 'no'), ('content_modified', 'n/a'),
                                     ('sealed', 'no')]))
        with open(os.path.join(dst, 'PROVENANCE.tsv'), 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=list(prov[0].keys()), delimiter='\t')
            w.writeheader()
            for r in prov:
                w.writerow(r)

    expected = {r['dataset_path'] for r in prov} | {'CHECKSUMS.md5', 'STALE_FILES.txt', 'PROVENANCE.tsv'}
    stale = []
    for dirpath, dirnames, filenames in os.walk(dst):
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), dst).replace(os.sep, '/')
            if rel.startswith(('external_reference/', 'analysis/')):
                continue          # owned by apriltag_reference.py, not by this build
            if rel not in expected:
                stale.append(rel)
    if stale:
        print(f'      !! {len(stale)} stale file(s) in the output tree, not produced by this build:')
        for rel in sorted(stale):
            print('         ' + rel)
        print('         DELETE THESE FILES, not this message: they are left over from an')
        print('         earlier build and are not part of the dataset. This script never deletes.')
    else:
        print('      no stale files in the output tree')

    print('[5/5] writing CHECKSUMS.md5 ...')
    lines = []
    for dirpath, dirnames, filenames in os.walk(dst):
        dirnames.sort()
        for name in sorted(filenames):
            if name in ('CHECKSUMS.md5', 'STALE_FILES.txt'):
                continue
            if os.path.relpath(os.path.join(dirpath, name), dst).replace(os.sep, '/') \
                    .startswith(('external_reference/', 'analysis/')):
                continue          # owned by the analysis scripts, checksummed by them
            p = os.path.join(dirpath, name)
            lines.append(f'{md5(p)}  {os.path.relpath(p, dst)}')
    with open(os.path.join(dst, 'CHECKSUMS.md5'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(f'      {len(lines)} files checksummed')

    print('\n--- record counts by resolution_method ---')
    for day in DAYS:
        tot = stats[(day, 'total', 'records')]
        esc = stats[(day, 'method', 'escalated')]
        print(f'  {day}: {tot} records total, {esc} escalated, {tot - esc} decision lines')

    print('\nDONE' if not (errors or missing or mismatch) else '\nDONE WITH PROBLEMS')


if __name__ == '__main__':
    main()
