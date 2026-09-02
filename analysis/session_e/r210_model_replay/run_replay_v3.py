#!/usr/bin/env python3
"""
R2-10 second-model replay runner, v2  --  ROBOT-D-26-01090 (RAS)

Replays the 69 archived L3b VLM decisions of Session E through one or more
alternative models.

WHAT VARIES. At the application interface, only the model identifier varies:
prompt text, image bytes, endpoint, parser, and the explicitly requested
sampling parameters are held fixed. Model-intrinsic tokenizer, chat template and
stop-token definitions necessarily vary with model identity -- they are part of
what a model IS, not separate experimental factors. They are recorded in the
provenance block, not controlled.

SCOPE. This exercises the L3b semantic destination-selection path only
(/api/chat, one user message, archived prompt + archived image_start). The
post-arrival visual-confirmation module (visual_confirmation_v2.py) is a
separate VLM interface with its own endpoint, prompt and inference settings and
is NOT covered here. Do not generalise a result from this runner to it.

WHY v2 EXISTS. v1 sent only {num_predict, temperature, num_ctx} and let every
other sampler parameter fall through to each model's own defaults. Those
defaults differ: qwen3.5 ships top_k 20 and presence_penalty 1.5, gemma4 ships
top_k 64 and no presence penalty. The arms were therefore not sampled alike, and
the runner had no way to show it, because it recorded the options REQUESTED
rather than the options APPLIED. v2 fixes both halves:

  * the sampler keys that have a documented justification are pinned explicitly
    -- the three the navigator sent, plus the three Session E model defaults,
    plus a seed. Every other sampler key is left to the single Ollama server
    installation in use and checked for model-specific overrides across arms,
    rather than pinned to an invented value (see OPTIONS below);
  * before each arm the runner reads the model's own parameters from /api/show,
    merges them under the request, and records the EFFECTIVE configuration —
    so any value we failed to pin is visible in the record instead of invisible;
  * a seed is derived PER RECORD and recorded, to improve run-level
    reproducibility. This is not a claim of bit-identical reproduction: GPU
    kernels, batching and Ollama build differences can still move a token.

WHY v3 EXISTS. v2 sent one seed for the whole run. That is worse than no seed at
all. Every reply starts from a near-identical distribution -- all 69 must open a
JSON object and emit the node_id key -- so one shared RNG state means the same
early draw is replayed on every record. The sampling error stops averaging out
and becomes correlated across the whole arm. Observed directly: qwen3.5:4b
failed to produce parseable JSON on 8 of the first 18 records under a single
seed, against 2, 2 and 3 of the same 18 in three unseeded passes the day before.
v3 derives the seed from the record key, so a run is still exactly reproducible
but the records are independent draws again.

Two further changes are about not losing data:

  * every output file carries a run tag and the runner REFUSES to overwrite an
    existing file. In v1 both the CSV and the raw JSONL were opened with "w",
    which silently destroyed pass1's raw text when pass2 started.
  * one warm-up call per arm, excluded from the results, so record 1 is not
    contaminated by model load time.

Usage
-----
    python3 run_replay_v3.py --models qwen3.5:4b --seed 1 --tag pass1 --limit 3
    python3 run_replay_v3.py --models qwen3.5:4b gemma4:e2b qwen3.5:9b --seed 1 --tag armsA

Outputs (written to ./results_v3/)
----------------------------------
    environment_<tag>.json            host / GPU / Ollama identity + EFFECTIVE options
    results_<model_slug>_<tag>.csv    one row per record, parsed fields
    raw_<model_slug>_<tag>.jsonl      full Ollama responses, unmodified
    RUN_LOG.txt

Nothing in this script needs the robots, the context server or ROS.
"""
import argparse, base64, csv, hashlib, json, os, platform, re, shutil
import subprocess, sys, time, urllib.request, urllib.error

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# The Session E control model. Its digest is recorded in sessions.csv on all 214
# audit sessions. If this model is in --models, the runner refuses to start unless
# the installed digest matches, because the whole point of the control arm is that
# it is the SAME model, not merely the same tag.
CONTROL_MODEL = "qwen3.5:4b"
CONTROL_DIGEST = ("0c8faadc50c205b83c634430c1dae6d1a4896c9b818cb8f290aa34d535265018")

# ---- inference conditions ---------------------------------------------------
# The first three are what vlm_navigator_node_v4_8_review.py :: call_vlm() sent
# explicitly (verified in source, lines 861-862). The rest were NOT sent by the
# navigator; they are qwen3.5:4b's own defaults, which is what actually acted
# during Session E, read from `ollama show --modelfile qwen3.5:4b` on the same
# host, with the same Ollama build (0.30.2) and the same model digest that the
# Session E navigator_startup records recorded contemporaneously.
#
# Pinning them to the Session E values rather than to neutral ones is deliberate:
# the control arm has to keep replicating the archive, and the question asked is
# whether another model works as a drop-in INTO THIS PIPELINE, so every arm is
# run under the pipeline's configuration.
# (a) VERIFIED: read from the navigator source, lines 861-862.
NAVIGATOR_SENT = {"num_predict": 500, "temperature": 0.3, "num_ctx": 16384}

# (b) VERIFIED: qwen3.5:4b's own Modelfile defaults, read with `ollama show` on
#     the Session E host, same Ollama build and same model digest that the
#     Session E navigator_startup records recorded contemporaneously. These are
#     the values that actually acted during Session E because the navigator did
#     not override them. gemma4 ships top_k 64 and no presence penalty, which is
#     precisely the confound this file exists to remove.
SESSION_E_MODEL_DEFAULTS = {"top_k": 20, "top_p": 0.95, "presence_penalty": 1.5}

# (c) plus a seed, added deliberately for the controlled replay. Session E sent
#     none.
#
# Every remaining sampler parameter is DELIBERATELY NOT PINNED. An earlier draft
# pinned seven of them to plausible Ollama defaults, which would have meant
# asserting values nobody observed during Session E.
#
# Be precise about what the check below does and does not do. It reads each
# model's Modelfile parameters from /api/show and detects MODEL-SPECIFIC
# OVERRIDES that differ across arms; if one model overrode a key, it would appear
# in that model's sampler view alone and the run would abort. For a key absent
# from every Modelfile, the built-in value is never read at all -- it is common
# across arms because all arms run through the same Ollama server installation.
# That is weaker than reading the value, and stronger than inventing one.
OPTIONS = dict(NAVIGATOR_SENT, **SESSION_E_MODEL_DEFAULTS)

# The controlled sampler. Equality between arms is judged on THESE keys only --
# the full list, not just the pinned ones, so that a key we did NOT pin cannot
# differ between models unnoticed. A model's template, stop tokens and tokenizer
# differ by construction, must not raise a false alarm, and are recorded as
# model-intrinsic configuration instead.
SAMPLER_KEYS = [
    "seed", "temperature", "top_k", "top_p", "min_p", "typical_p",
    "presence_penalty", "frequency_penalty", "repeat_penalty", "repeat_last_n",
    "mirostat", "penalize_newline", "num_predict", "num_ctx",
]
THINK   = False
ENDPOINT = "/api/chat"
TIMEOUT  = 300
# ----------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results_v3")


def md5_bytes(b):
    return hashlib.md5(b).hexdigest()


def slug(model):
    return re.sub(r"[^A-Za-z0-9._-]", "_", model)


def http_json(url, payload=None, timeout=30):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


# ---- parser contract ------------------------------------------------------
# Mirrors call_vlm() in vlm_navigator_node_v4_8_review.py up to the point where the
# original returns parsed.get('node_id') UNCHANGED. This runner deliberately does
# NOT coerce a string node_id into an integer: the original did not, so accepting
# {"node_id": "9"} here would inflate a second model's apparent contract compliance.
# The raw value and its type are recorded instead, and the layered outcome is
# resolved offline against the graph and the negation constraint.
def parse_response(result):
    """Returns a dict describing the outcome in separable layers."""
    msg = result.get("message") or {}
    raw_content = (msg.get("content") or "").strip()
    if not raw_content:
        raw_content = (msg.get("thinking") or "").strip()

    content = raw_content
    if "<think>" in content:
        i = content.rfind("</think>")
        if i != -1:
            content = content[i + 8:].strip()
    content = content.replace("```json", "").replace("```", "").strip()

    out = {"raw_content": raw_content, "json_parse": "none",
           "node_id_raw": "", "node_id_type": "missing",
           "node_id_int": "", "contract_ok": False, "reason": ""}

    parsed = None
    try:
        parsed = json.loads(content)
        out["json_parse"] = "direct"
    except json.JSONDecodeError:
        m = re.search(r"\{.*?\}", content, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                out["json_parse"] = "extracted"
            except json.JSONDecodeError:
                out["json_parse"] = "malformed"
        else:
            out["json_parse"] = "no_json"

    if not isinstance(parsed, dict):
        if parsed is not None:
            out["json_parse"] = "not_an_object"
        return out

    out["reason"] = str(parsed.get("reason", ""))[:500]
    if "node_id" not in parsed:
        return out
    nid = parsed["node_id"]
    out["node_id_raw"] = json.dumps(nid, ensure_ascii=False)
    out["node_id_type"] = type(nid).__name__
    # contract = the original contract: node_id is a JSON integer, not a string.
    if isinstance(nid, int) and not isinstance(nid, bool):
        out["node_id_int"] = nid
        out["contract_ok"] = True
    return out


def record_seed(base_seed, record_key):
    """A per-record seed: reproducible, but not shared between records.

    A single seed for a whole arm correlates the sampling error across records
    instead of averaging it -- see the v3 note in the module docstring. Deriving
    it from the record key keeps every run exactly reproducible (anyone can
    recompute this from base_seed and the key) while making the records
    independent draws again.
    """
    h = int(hashlib.md5(record_key.encode("utf-8")).hexdigest()[:8], 16)
    return (base_seed * 1_000_003 + h) % (2 ** 31 - 1)


def call_model(model, prompt, image_b64, options):
    messages = [{"role": "user", "content": prompt,
                 "images": [image_b64] if image_b64 else []}]
    payload = {"model": model, "stream": False, "messages": messages,
               "think": THINK, "options": options}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA_URL + ENDPOINT, data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        result = json.loads(resp.read())
    t1 = time.time()
    td = result.get("total_duration", 0)
    result["_wall_ms"] = round((t1 - t0) * 1000.0, 2)
    result["_total_ms"] = round(td / 1e6, 2) if td else 0.0
    result["_queue_ms"] = round(max(0.0, result["_wall_ms"] - result["_total_ms"]), 2)
    result["_request_sent_at"] = t0
    result["_response_at"] = t1
    return result


def _parse_show_parameters(show):
    """The model's OWN default sampler parameters, as Ollama reports them.

    /api/show returns them as a free-text block, one "name value" per line, the
    same text `ollama show --modelfile` prints as PARAMETER lines. These are the
    values that apply to any key the request does not set. v1 never read them,
    which is exactly why the arms differed without anyone noticing.
    """
    out = {}
    txt = show.get("parameters") or ""
    for line in txt.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        k, v = parts[0], parts[1].strip().strip('"')
        try:
            val = int(v)
        except ValueError:
            try:
                val = float(v)
            except ValueError:
                val = {"true": True, "false": False}.get(v.lower(), v)
        # A key may legitimately repeat -- `stop` usually does. Keeping only the
        # last one would silently hide stop tokens, so repeats become a list.
        if k in out:
            if not isinstance(out[k], list):
                out[k] = [out[k]]
            out[k].append(val)
        else:
            out[k] = val
    return out


def effective_options(model_defaults, requested):
    """What Ollama will actually apply: model defaults, overridden by request."""
    eff = dict(model_defaults)
    eff.update(requested)
    return eff


def sampler_view(effective):
    """The controlled sampler only.

    Arms are compared on this, not on the whole effective dictionary. Two models
    always differ in template, stop tokens and other Modelfile content; that is
    model identity, not a sampler confound, and folding it into the comparison
    would raise a false alarm on every run.
    """
    return {k: effective[k] for k in SAMPLER_KEYS if k in effective}


def model_identity(model):
    info = {"model": model, "digest": None, "quantization": None,
            "parameter_size": None, "family": None}
    try:
        show = http_json(OLLAMA_URL + "/api/show", {"model": model})
        d = show.get("details") or {}
        info["quantization"] = d.get("quantization_level")
        info["parameter_size"] = d.get("parameter_size")
        info["family"] = d.get("family")
        info["digest"] = show.get("digest")
        info["model_default_parameters"] = _parse_show_parameters(show)
        info["template"] = show.get("template")
        info["requested_options"] = OPTIONS
        eff = effective_options(info["model_default_parameters"], OPTIONS)
        info["effective_options"] = eff
        samp = sampler_view(eff)
        info["sampler_options"] = samp
        info["sampler_options_md5"] = md5_bytes(
            json.dumps(samp, sort_keys=True).encode())
        # Model-intrinsic settings: recorded, deliberately NOT harmonised.
        info["model_intrinsic"] = {
            k: v for k, v in info["model_default_parameters"].items()
            if k not in SAMPLER_KEYS}
        # A sampler key this model supplies that we failed to pin: the actual
        # defect class. Anything here can differ silently between arms.
        info["unpinned_sampler_keys"] = sorted(
            k for k in info["model_default_parameters"]
            if k in SAMPLER_KEYS and k not in OPTIONS)
    except Exception as ex:
        info["show_error"] = repr(ex)
    if not info["digest"]:
        try:
            for m in (http_json(OLLAMA_URL + "/api/tags").get("models") or []):
                if model in (m.get("name"), m.get("model")):
                    info["digest"] = m.get("digest")
                    info["size_bytes"] = m.get("size")
                    break
        except Exception as ex:
            info["tags_error"] = repr(ex)
    return info


def environment(models):
    env = {
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": platform.node(),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "ollama_url": OLLAMA_URL,
        "inference_options": OPTIONS,
        "think": THINK,
        "endpoint": ENDPOINT,
    }
    try:
        env["ollama_version"] = http_json(OLLAMA_URL + "/api/version").get("version")
    except Exception as ex:
        env["ollama_version_error"] = repr(ex)
    if shutil.which("nvidia-smi"):
        try:
            q = ("name,driver_version,memory.total,compute_cap")
            out = subprocess.run(
                ["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=20).stdout.strip()
            env["gpu"] = out
            env["gpu_driver_version"] = out.split(",")[1].strip() if "," in out else None
        except Exception as ex:
            env["gpu_error"] = repr(ex)
    else:
        env["gpu"] = "nvidia-smi not found"
    # Concurrency changes whether requests overlap, which would make every
    # latency figure meaningless. Record what the server was actually set to.
    env["ollama_env"] = {k: os.environ.get(k) for k in (
        "OLLAMA_NUM_PARALLEL", "OLLAMA_MAX_LOADED_MODELS", "OLLAMA_KEEP_ALIVE",
        "OLLAMA_FLASH_ATTENTION", "OLLAMA_KV_CACHE_TYPE")}
    env["models"] = {m: model_identity(m) for m in models}
    return env


def gpu_snapshot():
    if not shutil.which("nvidia-smi"):
        return None
    try:
        q = "memory.used,memory.total,utilization.gpu,temperature.gpu"
        return subprocess.run(
            ["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception as ex:
        return repr(ex)


# Latency naming, deliberately explicit. Session E's timing.vlm_ms is the CLIENT-SIDE
# wall time around the call, so client_wall_ms is the quantity comparable to it.
# ollama_total_ms is Ollama's own total_duration and is NOT the same measurement.
FIELDS = ["record_key", "experiment_id", "model", "model_digest", "quantization",
          "parameter_size", "prompt_md5", "image_md5",
          "json_parse", "node_id_raw", "node_id_type", "node_id_int", "contract_ok",
          "reason", "negation_forbidden_nodes",
          "client_wall_ms", "ollama_total_ms", "queue_ms", "load_ms",
          "prompt_eval_count", "prompt_eval_duration_ms",
          "eval_count", "eval_duration_ms", "tokens_per_sec",
          "done_reason", "error", "attempt", "timestamp_utc",
          # v2: the sampler is now part of the record, not an assumption.
          "seed_base", "seed", "sampler_options_md5", "run_tag"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True,
                    help="Ollama model identifiers. Include qwen3.5:4b as the "
                         "same-model control arm.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Replay only the first N records (smoke test).")
    ap.add_argument("--set", choices=["main", "no_image"], default="main",
                    help="main = the 69 image-backed records (default). "
                         "no_image = the 14 escalated prompts whose start frame "
                         "was never archived; replayed text-only, NOT comparable "
                         "to the original conditions. See PROTOCOL.md section 9.")
    ap.add_argument("--retries", type=int, default=2,
                    help="Retries on transport error only, never on a bad parse.")
    ap.add_argument("--seed", type=int, required=True,
                    help="Base seed for the pass. The seed actually sent is "
                         "derived per record as f(base_seed, record_key), so "
                         "records are independent draws while the run stays "
                         "reproducible; both values are written to the CSV. Use "
                         "the same base across model arms within a pass so each "
                         "record gets the same requested RNG initialisation in "
                         "every arm; use a different base per pass to measure "
                         "within-model variability. Statistical pairing is by "
                         "record_key, not by RNG seed.")
    ap.add_argument("--tag", required=True,
                    help="Run tag, e.g. pass1. Becomes part of every output "
                         "filename so no run can overwrite another.")
    ap.add_argument("--force", action="store_true",
                    help="Permit overwriting existing outputs for this tag. "
                         "Do not use to recover from a mistake; pick a new tag.")
    args = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.tag):
        sys.exit("--tag must be filename-safe.")
    # The seed varies per record, so it is NOT part of OPTIONS. It is added to a
    # copy at call time. The sampler-equality check below therefore compares the
    # arms on everything except the seed, which is identical across arms for any
    # given record by construction.

    os.makedirs(RESULTS, exist_ok=True)
    mfile = ("manifest_inputs.csv" if args.set == "main"
             else "manifest_escalated_no_image.csv")
    manifest = list(csv.DictReader(open(os.path.join(HERE, mfile), encoding="utf-8")))
    if args.limit:
        manifest = manifest[:args.limit]

    env = environment(args.models)

    # v1 merged every invocation into one environment.json and kept a .bak. That
    # made the provenance of any single run a reconstruction. v2 writes one
    # immutable file per run tag and never rewrites an existing one.
    env["run_tag"] = args.tag
    env["seed_base"] = args.seed
    env["seed_scheme"] = ("per record: (base_seed * 1000003 + "
                          "int(md5(record_key)[:8], 16)) % (2**31 - 1). A single "
                          "seed shared by every record correlates the sampling "
                          "error across records instead of averaging it; both "
                          "the base and the derived value are in the CSV.")
    env["set"] = args.set
    env["scope"] = ("L3b semantic destination selection only; the post-arrival "
                    "visual-confirmation VLM path is not covered")
    env["experiment_type"] = "controlled harmonized replay"
    env["experiment_note"] = (
        "The 69 prompts and images are an exact replay of the archived Session E "
        "L3b inputs. The replay explicitly fixes the three options sent by the "
        "original navigator, the three verified Qwen3.5:4b model defaults that "
        "were effective during Session E, and an added RNG seed. Other sampler "
        "parameters are not reconstructed historically; no model-specific override "
        "of those parameters is permitted to differ across arms, and all arms run "
        "through the same Ollama server installation. This is a controlled "
        "harmonized replay, not a bit-identical reproduction of Session E "
        "inference.")
    env["sampler_provenance"] = {
        "navigator_sent_verified": NAVIGATOR_SENT,
        "session_e_model_defaults_verified": SESSION_E_MODEL_DEFAULTS,
        "seed_added_for_controlled_replay": "per record, derived (see seed_scheme)",
        "other_sampler_keys": ("not pinned and not read; checked for "
                               "model-specific overrides differing across arms, "
                               "otherwise the same Ollama server defaults apply "
                               "to every arm (see ollama_version)"),
        "controlled_keys_compared": SAMPLER_KEYS,
    }
    envpath = os.path.join(RESULTS, f"environment_{args.tag}.json")

    # Hard gate: the control arm is only a control if it is the same model.
    if CONTROL_MODEL in args.models:
        got = (env["models"].get(CONTROL_MODEL) or {}).get("digest") or ""
        got = got.replace("sha256:", "")
        if not got:
            print(f"\n!! Could not read the digest of {CONTROL_MODEL}. Check it by hand\n"
                  f"   against {CONTROL_DIGEST[:12]}... before running.\n")
            sys.exit(3)
        if got != CONTROL_DIGEST:
            print(f"\n!! ABORT — {CONTROL_MODEL} is NOT the Session E model.\n"
                  f"   installed: {got}\n   expected : {CONTROL_DIGEST}\n"
                  f"   Do not pull or re-tag it. Recover the original model first.\n")
            sys.exit(3)
        print(f"control model digest verified: {CONTROL_MODEL} = {got[:16]}...")

    # Refuse to destroy an earlier run. This is the check that was missing when
    # pass2 overwrote pass1's raw output.
    suffix = "" if args.set == "main" else "_noimage"
    planned = [envpath]
    for m in args.models:
        planned += [os.path.join(RESULTS, f"results_{slug(m)}{suffix}_{args.tag}.csv"),
                    os.path.join(RESULTS, f"raw_{slug(m)}{suffix}_{args.tag}.jsonl")]
    clash = [p for p in planned if os.path.exists(p)]
    if clash and not args.force:
        print("\n!! ABORT — these outputs already exist:")
        for p in clash:
            print("   " + os.path.relpath(p, HERE))
        print("   Choose a different --tag. Do not pass --force unless you "
              "intend to destroy them.\n")
        sys.exit(4)

    # Say plainly what will actually be applied, and refuse to run if the arms
    # would not be sampled alike. This run exists to remove that ambiguity, so a
    # warning is not enough: an unequal sampler is a stop condition.
    print("\n--- controlled sampler per arm ---")
    for m in args.models:
        info = env["models"].get(m, {})
        print(f"  {m}  sampler_md5="
              f"{(info.get('sampler_options_md5') or '?')[:12]}")
        print("    " + json.dumps(info.get("sampler_options") or {}, sort_keys=True))
        intrinsic = info.get("model_intrinsic") or {}
        if intrinsic:
            print(f"    model-intrinsic (recorded, not harmonised): "
                  f"{json.dumps(intrinsic, sort_keys=True)}")
        stray = info.get("unpinned_sampler_keys") or []
        if stray:
            print(f"    !! UNPINNED SAMPLER KEYS from this model: {stray}")

    # No provenance, no experiment. Without a sampler hash we cannot demonstrate
    # what was applied, and the equality check below would compare None to None.
    for m in args.models:
        info = env["models"].get(m) or {}
        if not info.get("sampler_options_md5"):
            print(f"\n!! ABORT — sampler provenance unavailable for {m}.")
            print(f"   /api/show error: {info.get('show_error')}")
            print(f"   /api/tags error: {info.get('tags_error')}")
            print("   The run cannot demonstrate what sampler was applied, so it\n"
                  "   will not start.\n")
            sys.exit(5)

    by_md5 = {}
    for m in args.models:
        by_md5.setdefault(
            (env["models"].get(m) or {}).get("sampler_options_md5"), []).append(m)
    if len(by_md5) > 1:
        print("\n!! ABORT — the arms would NOT be sampled identically.")
        for md5v, ms in by_md5.items():
            print(f"   {(md5v or '?')[:12]}  {', '.join(ms)}")
        keys = set()
        views = [(env["models"].get(m) or {}).get("sampler_options") or {}
                 for m in args.models]
        for k in SAMPLER_KEYS:
            if len({json.dumps(v.get(k)) for v in views}) > 1:
                keys.add(k)
        print(f"   differing keys: {sorted(keys)}")
        print("   Pin them in OPTIONS. The point of this run is to remove this\n"
              "   ambiguity, so it will not start until the sampler is equal.\n")
        sys.exit(5)
    print(f"  all arms share one controlled sampler "
          f"({list(by_md5)[0][:12]})")
    print(f"  seed is not in the block above: it is derived per record from "
          f"base {args.seed},")
    print(f"  identically in every arm. Example: "
          f"{manifest[0]['record_key']} -> "
          f"{record_seed(args.seed, manifest[0]['record_key'])}\n")

    env["records"] = len(manifest)
    with open(envpath, "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2, ensure_ascii=False)

    log = open(os.path.join(RESULTS, "RUN_LOG.txt"), "a", encoding="utf-8")

    def say(s):
        print(s); log.write(s + "\n"); log.flush()

    say(f"\n===== run started {env['captured_at_utc']}  set={args.set}  "
        f"tag={args.tag}  seed_base={args.seed}  records={len(manifest)} =====")

    for model in args.models:
        ident = env["models"].get(model, {})
        s = slug(model)
        # Exclusive creation: if the file appeared since the pre-flight check,
        # this raises instead of truncating it.
        mode = "w" if args.force else "x"
        fcsv = open(os.path.join(RESULTS, f"results_{s}{suffix}_{args.tag}.csv"),
                    mode, encoding="utf-8", newline="")
        w = csv.DictWriter(fcsv, fieldnames=FIELDS); w.writeheader()
        fraw = open(os.path.join(RESULTS, f"raw_{s}{suffix}_{args.tag}.jsonl"),
                    mode, encoding="utf-8")
        t_model = time.time()

        say(f"  [{model}] gpu before load: {gpu_snapshot()}")
        # One warm-up call, discarded. In v1 the first record carried the model
        # load time and had to be excluded from latency stats after the fact.
        #
        # It carries an image on the main set. A text-only warm-up wakes the
        # language model but not necessarily the vision projector, so record 1
        # would still absorb the cost of initialising the multimodal path. The
        # first record's image is reused: the experimental prompt is not sent and
        # the reply is never recorded as an observation.
        warm_image_b64 = None
        if args.set == "main" and manifest:
            warm_image_b64 = base64.b64encode(
                open(os.path.join(HERE, manifest[0]["image_file"]), "rb").read()
            ).decode()
        try:
            warm = call_model(model, "Reply with the single character: 1",
                              warm_image_b64,
                              dict(OPTIONS, num_predict=4,
                                   seed=record_seed(args.seed, "__warmup__")))
            say(f"  [{model}] warm-up ok ("
                f"{'with image' if warm_image_b64 else 'text only'}), load_ms="
                f"{round((warm.get('load_duration') or 0)/1e6, 1)} "
                f"(discarded, not in results)")
        except Exception as ex:
            say(f"  [{model}] warm-up FAILED: {ex!r} — continuing, but record 1 "
                f"will include load time")
        say(f"  [{model}] gpu after load : {gpu_snapshot()}")

        for i, row in enumerate(manifest, 1):
            prompt = open(os.path.join(HERE, row["prompt_file"]),
                          encoding="utf-8").read()
            pmd5 = md5_bytes(prompt.encode("utf-8"))
            if pmd5 != row["prompt_md5"]:
                say(f"  !! prompt md5 mismatch on {row['record_key']} — ABORT")
                sys.exit(2)
            if args.set == "main":
                raw_img = open(os.path.join(HERE, row["image_file"]), "rb").read()
                imd5 = md5_bytes(raw_img)
                if imd5 != row["image_md5"]:
                    say(f"  !! image md5 mismatch on {row['record_key']} — ABORT")
                    sys.exit(2)
                image_b64 = base64.b64encode(raw_img).decode()
            else:
                imd5, image_b64 = "", None

            rseed = record_seed(args.seed, row["record_key"])
            call_options = dict(OPTIONS, seed=rseed)

            rec = {k: "" for k in FIELDS}
            rec.update(record_key=row["record_key"],
                       experiment_id=row.get("experiment_id", ""),
                       model=model, model_digest=ident.get("digest"),
                       quantization=ident.get("quantization"),
                       parameter_size=ident.get("parameter_size"),
                       prompt_md5=pmd5, image_md5=imd5,
                       negation_forbidden_nodes=row.get("negation_forbidden_nodes", ""),
                       seed_base=args.seed, seed=rseed, run_tag=args.tag,
                       sampler_options_md5=ident.get("sampler_options_md5", ""),
                       timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            result = None
            for attempt in range(1, args.retries + 2):
                rec["attempt"] = attempt
                try:
                    result = call_model(model, prompt, image_b64, call_options)
                    break
                except Exception as ex:
                    rec["error"] = repr(ex)[:300]
                    say(f"  [{model}] {row['record_key']} transport error "
                        f"attempt {attempt}: {rec['error']}")
                    time.sleep(3)
            if result is None:
                rec["json_parse"] = "transport_failed"
                w.writerow(rec); fcsv.flush(); continue

            po = parse_response(result)
            ec = result.get("eval_count") or 0
            ed = result.get("eval_duration") or 0
            rec.update(
                json_parse=po["json_parse"], node_id_raw=po["node_id_raw"],
                node_id_type=po["node_id_type"], node_id_int=po["node_id_int"],
                contract_ok=po["contract_ok"], reason=po["reason"],
                client_wall_ms=result["_wall_ms"],
                ollama_total_ms=result["_total_ms"],
                queue_ms=result["_queue_ms"],
                load_ms=round((result.get("load_duration") or 0) / 1e6, 2),
                prompt_eval_count=result.get("prompt_eval_count"),
                prompt_eval_duration_ms=round(
                    (result.get("prompt_eval_duration") or 0) / 1e6, 2),
                eval_count=ec,
                eval_duration_ms=round(ed / 1e6, 2),
                tokens_per_sec=round(ec / (ed / 1e9), 1) if ed else 0.0,
                done_reason=result.get("done_reason"), error="")
            w.writerow(rec); fcsv.flush()
            fraw.write(json.dumps(
                {"record_key": row["record_key"], "model": model,
                 "raw_content": po["raw_content"], "response": result},
                ensure_ascii=False) + "\n")
            fraw.flush()
            say(f"  [{model}] {i:3d}/{len(manifest)} {row['record_key']} "
                f"-> node_id={po['node_id_raw'] or '-'} ({po['json_parse']}, "
                f"contract={'ok' if po['contract_ok'] else 'FAIL'}) "
                f"{result['_wall_ms']:.0f} ms wall")

        fcsv.close(); fraw.close()
        say(f"  [{model}] done in {time.time()-t_model:.0f} s")

    say(f"===== run complete  tag={args.tag} seed_base={args.seed} =====")
    log.close()


if __name__ == "__main__":
    main()
