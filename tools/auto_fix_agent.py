#!/usr/bin/env python3
"""
Auto-Fix Agent — School MIS
============================
Reads unresolved backend errors from /api/error-logs, generates a targeted
fix via Claude API, tests it in an isolated Docker sandbox, and opens a
GitHub PR if the smoke tests pass.

Safety rules (hard-coded, not configurable):
  - Never auto-deploys. Every fix goes through a PR + human review.
  - Never touches auth, payment, or core DB files.
  - Only attempts one fix per error signature every 24 hours.
  - Requires Claude confidence >= 0.75 before applying any change.
  - Sandbox must pass before a PR is created.
  - Always returns git to main branch, even on failure.

Usage:
  python tools/auto_fix_agent.py [--dry-run]

Required env vars (copy tools/.env.example → tools/.env and source it):
  ANTHROPIC_API_KEY       Claude API key
  MIS_API_URL             e.g. http://localhost or https://maarifahub.co.tz
  MIS_SUPERADMIN_USER     superadmin username
  MIS_SUPERADMIN_PASS     superadmin password

Optional:
  AUTOFIX_MAX_PER_RUN     max errors to attempt in one run (default 1)
  AUTOFIX_RETRY_HOURS     hours before retrying a failed error (default 24)
  AUTOFIX_MIN_CONFIDENCE  minimum Claude confidence 0.0-1.0 (default 0.75)
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ── Third-party deps (installed via tools/requirements.txt) ───────────────────
try:
    import anthropic
except ImportError:
    sys.exit("ERROR: run  pip install -r tools/requirements.txt  first")

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT       = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "tools" / ".autofix_state.json"
LOG_FILE   = ROOT / "tools" / "autofix.log"

# ── Config from env ───────────────────────────────────────────────────────────

API_KEY        = os.environ.get("ANTHROPIC_API_KEY", "")
MIS_URL        = os.environ.get("MIS_API_URL", "http://localhost").rstrip("/")
SA_USER        = os.environ.get("MIS_SUPERADMIN_USER", "")
SA_PASS        = os.environ.get("MIS_SUPERADMIN_PASS", "")
MAX_PER_RUN    = int(os.environ.get("AUTOFIX_MAX_PER_RUN", "1"))
RETRY_HOURS    = int(os.environ.get("AUTOFIX_RETRY_HOURS", "24"))
MIN_CONFIDENCE = float(os.environ.get("AUTOFIX_MIN_CONFIDENCE", "0.75"))

# ── Safety: files the agent must NEVER modify ─────────────────────────────────

BLACKLISTED_FILES = {
    "backend/deps.py",
    "backend/main.py",
    "backend/routers/auth.py",
    "backend/core/security.py",
    "backend/core/authz.py",
    "database/db.py",
}

# Never touch a file whose content mentions these (payment / crypto critical) ─
SENSITIVE_PATTERNS = re.compile(
    r"bcrypt|hashpw|secret_key|payment|flutterwave|paystack|stripe|crypto",
    re.I,
)

# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO") -> None:
    line = f"[{datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── State (persisted between runs) ────────────────────────────────────────────

def _load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except Exception:
        pass
    return {"attempts": {}}

def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

def _signature(err: dict) -> str:
    raw = f"{err.get('error_type','')}::{err.get('path','')}::{(err.get('message') or '')[:80]}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]

def _should_attempt(sig: str, state: dict) -> bool:
    entry = state["attempts"].get(sig)
    if not entry:
        return True
    if entry.get("result") == "pr_opened":
        return False   # already fixed — wait for merge
    last = datetime.fromisoformat(entry["last_attempt"])
    return datetime.utcnow() - last >= timedelta(hours=RETRY_HOURS)

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _http(method: str, path: str, body: dict | None = None,
          headers: dict | None = None) -> tuple[int, dict]:
    url  = MIS_URL + "/api" + path
    data = json.dumps(body).encode() if body else None
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req  = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}

def _get_token() -> str | None:
    if not SA_USER or not SA_PASS:
        log("MIS_SUPERADMIN_USER / MIS_SUPERADMIN_PASS not set", "ERROR")
        return None
    status, data = _http("POST", "/auth/login", {"username": SA_USER, "password": SA_PASS})
    token = data.get("token")
    if status != 200 or not token:
        log(f"Login failed (HTTP {status}): {data}", "ERROR")
        return None
    return token

def _fetch_errors(token: str) -> list[dict]:
    status, data = _http("GET", "/error-logs?resolved=0&source=backend&limit=50",
                         headers={"Authorization": f"Bearer {token}"})
    if status != 200:
        log(f"Failed to fetch errors (HTTP {status})", "ERROR")
        return []
    return data.get("items", [])

def _fetch_full_error(error_id: int, token: str) -> dict | None:
    status, data = _http("GET", f"/error-logs/{error_id}",
                         headers={"Authorization": f"Bearer {token}"})
    return data if status == 200 else None

def _mark_resolved(error_id: int, token: str) -> None:
    _http("POST", f"/error-logs/{error_id}/resolve",
          headers={"Authorization": f"Bearer {token}"})

# ── Source-file detection ─────────────────────────────────────────────────────

_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+)')

def _find_source_file(stack: str) -> str | None:
    """Walk traceback bottom-up, return the first fixable project file."""
    for filepath, _ in reversed(_FRAME_RE.findall(stack or "")):
        if "__pycache__" in filepath or filepath.endswith("__init__.py"):
            continue
        if "backend/" not in filepath:
            continue
        # Normalise to project-relative path
        rel = "backend/" + filepath.split("backend/", 1)[-1]
        if rel in BLACKLISTED_FILES:
            continue
        abs_p = ROOT / rel
        if not abs_p.exists():
            continue
        # Skip files with sensitive content
        if SENSITIVE_PATTERNS.search(abs_p.read_text()):
            continue
        return rel
    return None

# ── Claude analysis ───────────────────────────────────────────────────────────

_PROMPT = """You are an expert Python/FastAPI/PostgreSQL developer.
The backend runs FastAPI + psycopg2. All DB access must use the helper functions
fetch_one, fetch_all, execute from backend.core.db — never raw psycopg2 connections.

## Error
Type:    {error_type}
Endpoint:{path}
Message: {message}

## Traceback
```
{stack}
```

## File to fix: {filepath}
```python
{source}
```

Generate a minimal, targeted fix. Respond ONLY with valid JSON — no markdown fences:
{{
  "confidence": 0.0,
  "explanation": "one sentence describing the fix",
  "changes": [
    {{ "old": "exact string to replace", "new": "replacement string" }}
  ]
}}

Rules:
- Fix ONLY what caused this specific error. Nothing else.
- Keep changes as small as possible.
- Do not add new imports that aren't already in the file unless essential.
- Do not change function signatures, route paths, or public APIs.
- If you cannot fix safely, set confidence below {min_confidence} and changes to [].
"""

def _analyze(err: dict, filepath: str, source: str) -> dict | None:
    client = anthropic.Anthropic(api_key=API_KEY)
    prompt = _PROMPT.format(
        error_type=err.get("error_type") or "Unknown",
        path=err.get("path") or "",
        message=(err.get("message") or "")[:800],
        stack=(err.get("stack") or "")[:4000],
        filepath=filepath,
        source=source[:6000],
        min_confidence=MIN_CONFIDENCE,
    )
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Strip accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.M).strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log(f"Claude returned invalid JSON: {e}", "WARN")
        return None
    except Exception as e:
        log(f"Claude API error: {e}", "ERROR")
        return None

# ── Patch application ─────────────────────────────────────────────────────────

def _apply(filepath: str, changes: list[dict]) -> tuple[bool, str]:
    path = ROOT / filepath
    text = path.read_text()
    orig = text
    for i, c in enumerate(changes):
        old, new = c.get("old", ""), c.get("new", "")
        if not old:
            return False, f"change {i}: empty 'old'"
        if old not in text:
            return False, f"change {i}: pattern not found:\n{old[:200]}"
        text = text.replace(old, new, 1)
    if text == orig:
        return False, "no effective change"
    path.write_text(text)
    return True, ""

# ── Git ───────────────────────────────────────────────────────────────────────

def _git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git"] + list(args), cwd=ROOT,
                       capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()

def _cmd(*args: str) -> tuple[int, str]:
    r = subprocess.run(list(args), cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()

# ── Docker sandbox ────────────────────────────────────────────────────────────

COMPOSE_TEST = ROOT / "docker-compose.test.yml"

def _sandbox_up() -> tuple[bool, str]:
    log("  Building sandbox…")
    code, out = _cmd("docker", "compose", "-f", str(COMPOSE_TEST),
                     "up", "--build", "-d", "--wait", "--wait-timeout", "120")
    if code != 0:
        return False, f"sandbox start failed:\n{out[-600:]}"
    return True, ""

def _sandbox_down() -> None:
    _cmd("docker", "compose", "-f", str(COMPOSE_TEST),
         "down", "-v", "--remove-orphans")

def _run_smoketest() -> tuple[bool, str]:
    code, out = _cmd("python", str(ROOT / "tools" / "smoketest.py"))
    return code == 0, out

def _test_in_sandbox() -> tuple[bool, str]:
    if not COMPOSE_TEST.exists():
        return False, "docker-compose.test.yml not found"
    try:
        ok, msg = _sandbox_up()
        if not ok:
            return False, msg
        time.sleep(3)
        log("  Running smoke tests…")
        return _run_smoketest()
    finally:
        _sandbox_down()

# ── PR creation ───────────────────────────────────────────────────────────────

def _create_pr(branch: str, err: dict, analysis: dict, smoke_out: str) -> str | None:
    title = f"[autofix] {err.get('error_type','Error')} on {err.get('path','')}"
    body = (
        "## Auto-generated fix\n\n"
        f"**Error type:** `{err.get('error_type','')}`  \n"
        f"**Endpoint:** `{err.get('path','')}`  \n"
        f"**Message:** {(err.get('message') or '')[:300]}\n\n"
        f"## What changed\n{analysis.get('explanation','')}\n\n"
        f"## Sandbox smoke-test output\n```\n{smoke_out[:600]}\n```\n\n"
        f"**Confidence:** {analysis.get('confidence', 0):.0%}  \n"
        "**Status:** Passed Docker sandbox tests before this PR was opened.\n\n"
        "> This PR was opened automatically. **Human review required before merging.**\n\n"
        "_Generated by `tools/auto_fix_agent.py` using Claude Sonnet 4.6_"
    )
    # Ensure the autofix label exists (ignore error if already present)
    _cmd("gh", "label", "create", "autofix", "--color", "0075ca",
         "--description", "Auto-generated fix", "--force")

    code, out = _cmd("gh", "pr", "create",
                     "--title", title,
                     "--body", body,
                     "--base", "main",
                     "--head", branch,
                     "--label", "autofix")
    if code != 0:
        log(f"  gh pr create failed: {out}", "ERROR")
        return None
    return out.strip().split("\n")[-1]

# ── Main pipeline ─────────────────────────────────────────────────────────────

def _process(err: dict, state: dict, token: str, dry_run: bool) -> str:
    """Returns: pr_opened | sandbox_failed | fix_failed | skipped | no_source"""
    sig  = _signature(err)
    eid  = err.get("id")
    log(f"  #{eid}  {err.get('error_type')}  {err.get('path')}")

    full = _fetch_full_error(eid, token) if eid else err
    if not full:
        return "skipped"

    # Find and validate source file
    src_file = _find_source_file(full.get("stack") or "")
    if not src_file:
        log("    No fixable source file in traceback")
        return "no_source"
    log(f"    Source: {src_file}")

    source = (ROOT / src_file).read_text()

    # Claude analysis
    log("    Asking Claude…")
    analysis = _analyze(full, src_file, source)
    if not analysis:
        return "fix_failed"

    confidence = float(analysis.get("confidence") or 0)
    changes    = analysis.get("changes") or []
    explanation = analysis.get("explanation") or ""
    log(f"    Confidence {confidence:.0%} | {len(changes)} change(s)")
    log(f"    {explanation}")

    if confidence < MIN_CONFIDENCE:
        log(f"    Confidence too low ({confidence:.0%} < {MIN_CONFIDENCE:.0%})")
        return "skipped"
    if not changes:
        log("    No changes returned")
        return "skipped"

    if dry_run:
        log("    [DRY RUN] Would apply:")
        for c in changes:
            log(f"      - {c.get('old','')[:80]!r} → {c.get('new','')[:80]!r}")
        return "skipped"

    # Create branch
    ts     = datetime.utcnow().strftime("%Y%m%d-%H%M")
    slug   = re.sub(r"[^a-z0-9]", "-", (err.get("error_type") or "error").lower())[:30]
    branch = f"autofix/{ts}-{slug}"

    code, out = _git("checkout", "-b", branch)
    if code != 0:
        log(f"    git checkout -b failed: {out}", "ERROR")
        return "fix_failed"

    result = "fix_failed"
    try:
        ok, msg = _apply(src_file, changes)
        if not ok:
            log(f"    Apply failed: {msg}", "ERROR")
            return "fix_failed"

        # Commit
        _git("add", src_file)
        commit_msg = (
            f"autofix: {explanation[:72]}\n\n"
            f"Fixes {err.get('error_type')} on {err.get('path')}\n"
            f"Error: {(err.get('message') or '')[:200]}\n\n"
            "Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
        )
        code, out = _git("commit", "-m", commit_msg)
        if code != 0:
            log(f"    git commit failed: {out}", "ERROR")
            return "fix_failed"

        # Sandbox
        log("    Testing in Docker sandbox…")
        passed, smoke_out = _test_in_sandbox()
        log(f"    Sandbox: {'PASS' if passed else 'FAIL'}")

        if not passed:
            log(f"    {smoke_out[-300:]}", "WARN")
            result = "sandbox_failed"
            return "sandbox_failed"

        # Push + PR
        code, out = _git("push", "-u", "origin", branch)
        if code != 0:
            log(f"    git push failed: {out}", "ERROR")
            return "fix_failed"

        pr_url = _create_pr(branch, full, analysis, smoke_out)
        if not pr_url:
            return "fix_failed"

        log(f"    PR: {pr_url}")
        result = "pr_opened"
        state["attempts"][sig] = {
            "last_attempt": datetime.utcnow().isoformat(),
            "result": "pr_opened",
            "branch": branch,
            "pr_url": pr_url,
            "explanation": explanation,
        }
        _save_state(state)
        return "pr_opened"

    finally:
        _git("checkout", "main")
        if result not in ("pr_opened",):
            # Clean up failed branch locally (keep remote if it was pushed)
            _git("branch", "-D", branch)
        # Record attempt so we don't retry immediately
        if result != "pr_opened":
            state["attempts"].setdefault(sig, {}).update({
                "last_attempt": datetime.utcnow().isoformat(),
                "result": result,
            })
            _save_state(state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-Fix Agent for School MIS")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making any changes")
    args = parser.parse_args()
    dry_run = args.dry_run or (os.environ.get("AUTOFIX_DRY_RUN", "0") == "1")

    log("=" * 55)
    log("Auto-Fix Agent starting" + (" [DRY RUN]" if dry_run else ""))
    log("=" * 55)

    if not API_KEY:
        sys.exit("ERROR: ANTHROPIC_API_KEY is not set")

    token = _get_token()
    if not token:
        sys.exit("ERROR: Could not authenticate with the MIS API")

    log(f"Authenticated as superadmin at {MIS_URL}")

    errors = _fetch_errors(token)
    log(f"Fetched {len(errors)} unresolved backend error(s)")

    state = _load_state()

    # Deduplicate by signature
    seen: set[str] = set()
    candidates: list[dict] = []
    for err in errors:
        sig = _signature(err)
        if sig in seen:
            continue
        seen.add(sig)
        if _should_attempt(sig, state):
            candidates.append(err)
        else:
            log(f"  Skip (recently attempted): {err.get('error_type')} on {err.get('path')}")

    if not candidates:
        log("No new errors to attempt. Done.")
        return

    attempted = min(len(candidates), MAX_PER_RUN)
    log(f"Will attempt {attempted} error(s)\n")

    results = {"pr_opened": 0, "sandbox_failed": 0, "fix_failed": 0,
               "skipped": 0, "no_source": 0}

    for err in candidates[:MAX_PER_RUN]:
        outcome = _process(err, state, token, dry_run)
        results[outcome] = results.get(outcome, 0) + 1

    log("")
    log("=" * 55)
    log(f"Done.  PRs opened: {results['pr_opened']}  "
        f"Sandbox failed: {results['sandbox_failed']}  "
        f"No fix: {results['fix_failed'] + results['no_source'] + results['skipped']}")
    log("=" * 55)


if __name__ == "__main__":
    main()
