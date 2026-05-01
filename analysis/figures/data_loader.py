"""data_loader.py — Common data extraction from audit logs.

Used by all figure scripts. Reads JSONL audit files from the repository
data/ directory and extracts scenario-level decisions.

Usage:
    from data_loader import load_all_sessions, classify
"""
import json
import os
from pathlib import Path
from collections import Counter

# Repository root (2 levels up from analysis/figures/)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"


def classify(instruction):
    """Classify an instruction into a scenario ID or None.
    
    Uses substring matching to handle minor typos and variations
    in the experimental data (e.g., 'sto stop' vs 'to stop').
    """
    if not instruction:
        return None
    instr = instruction.lower().strip()
    
    if 'short break for personal needs' in instr:
        return 'S1'
    if 'washroom got on fire' in instr:
        return 'S2'
    if 'too hot in here' in instr and 'fresh air' in instr:
        return 'S3old'
    if 'sit and relax' in instr:
        return 'S3new'
    if instr == 'go to lab_cb204':
        return 'S4'
    if instr == 'go to cb203 entrance':
        return 'S4_cb203'
    if 'closest plant' in instr:
        return 'S5'
    
    return None


M3_SCENARIOS = {'S1', 'S2', 'S3old', 'S3new'}
DETERMINISTIC_SCENARIOS = {'S4', 'S4_cb203', 'S5'}
ALL_SCENARIOS = M3_SCENARIOS | DETERMINISTIC_SCENARIOS


def load_decisions(audit_dir):
    """Load all decision entries from JSONL files in a directory."""
    decisions = []
    audit_path = Path(audit_dir)
    if not audit_path.exists():
        return decisions
    for f in sorted(audit_path.glob('*.jsonl')):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get('_type') == 'decision':
                        decisions.append(entry)
                except json.JSONDecodeError:
                    continue
    return decisions


def load_all_sessions():
    """Load decisions from all three sessions with scenario classification."""
    sessions = {}
    for session_id in ['session_a', 'session_b', 'session_c']:
        audit_dir = DATA_DIR / session_id / 'audits'
        all_decisions = load_decisions(audit_dir)
        for d in all_decisions:
            d['scenario'] = classify(d.get('instruction', ''))
        sessions[session_id.split('_')[1]] = all_decisions
    return sessions


def get_scenario_decisions(session_decisions, scenario_id):
    """Filter decisions by scenario ID."""
    return [d for d in session_decisions if d.get('scenario') == scenario_id]


def get_m3_decisions(session_decisions):
    """Get all M3 preference decisions."""
    return [d for d in session_decisions if d.get('scenario') in M3_SCENARIOS]


def get_deterministic_decisions(session_decisions):
    """Get all deterministic control decisions."""
    return [d for d in session_decisions if d.get('scenario') in DETERMINISTIC_SCENARIOS]


def get_resolve_times(decisions):
    """Extract resolve_ms from a list of decisions."""
    return [d['timing']['resolve_ms'] for d in decisions
            if 'timing' in d and 'resolve_ms' in d['timing']]


def get_vlm_times(decisions):
    """Extract vlm_ms from L3b decisions."""
    return [d['timing']['vlm_ms'] for d in decisions
            if d.get('resolution_method') == 'L3b_vlm'
            and 'timing' in d and 'vlm_ms' in d['timing']]


if __name__ == '__main__':
    sessions = load_all_sessions()
    total_scenario = 0
    for sid, decs in sessions.items():
        scenario_decs = [d for d in decs if d.get('scenario')]
        total_scenario += len(scenario_decs)
        print(f"Session {sid}: {len(decs)} total, {len(scenario_decs)} scenario")
        counts = Counter(d['scenario'] for d in scenario_decs)
        for s, c in sorted(counts.items()):
            print(f"  {s}: {c}")
    print(f"\nTotal scenario: {total_scenario}")
    
    b_decs = [d for d in sessions['b'] if d.get('scenario')]
    m3_b = get_m3_decisions(sessions['b'])
    print(f"\nSession B verification: {len(b_decs)} scenario, {len(m3_b)} M3")
