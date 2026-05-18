
# K16: Concurrent-Spawn-Mutex (fcntl-based, Trinity-CONSERVATIVE 2026-05-17)
def k16_lock_or_exit(df_name: str):
    """Acquire exclusive lock or exit(3). Prevents concurrent DF runs."""
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)


# K13: External-Anchor-Mock-RFC3161 (Trinity-CONSERVATIVE 2026-05-17)
def k13_anchor(payload_hash: str) -> dict:
    """Mock RFC3161-style timestamp anchor."""
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }


# K12: HMAC-SHA256-Provenance (Trinity-CONSERVATIVE 2026-05-17)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-conservative-v1") -> dict:
    """Returns payload_hash + HMAC-SHA256 signature."""
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

"""
df-163-engine.py

LexVance-Wegzugssteuer-Risiko-Tracker.
Mock-first tracker for per-client Wegzugsteuer deferral risk dimensions.
"""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone


DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-163.lock")
DF_ID = "163"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-163"
    iso_timestamp: str = ""
    source: str = "mock"
    clients_count: int = 0
    stundungs_open: int = 0
    total_value_eur: float = 0.0
    risk_per_client: dict = field(default_factory=dict)
    audit_findings: list = field(default_factory=list)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        first = p.stat()
        time.sleep(0.05)
        second = p.stat()
    except OSError:
        return False
    same_size = first.st_size == second.st_size
    same_mtime = first.st_mtime == second.st_mtime
    old_enough = (time.time() - second.st_mtime) >= min_age_sec
    return same_size and same_mtime and old_enough


def acquire_lock_with_identity() -> bool:
    now = time.time()
    stale_after_sec = 6 * 60 * 60

    try:
        LOCK_DIR.mkdir(mode=0o700)
        identity = {
            "df": DF_ID,
            "pid": os.getpid(),
            "created_at": iso_now(),
            "cwd": str(Path.cwd()),
        }
        (LOCK_DIR / "identity.json").write_text(
            json.dumps(identity, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except FileExistsError:
        pass
    except OSError:
        return False

    try:
        age = now - LOCK_DIR.stat().st_mtime
    except OSError:
        return False

    if age < stale_after_sec:
        return False

    try:
        for child in LOCK_DIR.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
        LOCK_DIR.rmdir()
    except OSError:
        return False

    try:
        LOCK_DIR.mkdir(mode=0o700)
        identity = {
            "df": DF_ID,
            "pid": os.getpid(),
            "created_at": iso_now(),
            "cwd": str(Path.cwd()),
            "recovered_stale_lock": True,
        }
        (LOCK_DIR / "identity.json").write_text(
            json.dumps(identity, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def release_lock() -> None:
    try:
        for child in LOCK_DIR.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
        LOCK_DIR.rmdir()
    except FileNotFoundError:
        return
    except OSError:
        return


def k17_pre_action_verification(anchors) -> dict:
    missing = []
    for anchor in anchors:
        if anchor is None:
            missing.append("")
            continue
        value = Path(anchor) if not isinstance(anchor, Path) else anchor
        if not value.exists():
            missing.append(str(value))

    env_tag = os.environ.get("DF_163_ENV_TAG", "local")
    return {
        "ok": len(missing) == 0,
        "missing_anchors": missing,
        "env_tag": env_tag,
    }


def _is_real_api_enabled() -> bool:
    raw = os.environ.get("DF_163_REAL_API_ENABLED", "false").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []
    matches = []
    seen = set()
    for match in DECISION_KEYWORDS_REGEX.finditer(str(text)):
        token = match.group(0)
        key = token.lower()
        if key not in seen:
            seen.add(key)
            matches.append(token)
    return matches


def assert_no_decision_keywords(output) -> None:
    text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    matches = scan_output_for_decision_keywords(text)
    if matches:
        raise ValueError("Q_0/K_0 block: restricted terms found: " + ", ".join(matches))


def _mock_tracker_output() -> TrackerOutput:
    return TrackerOutput(
        iso_timestamp=iso_now(),
        source="mock",
        clients_count=3,
        stundungs_open=2,
        total_value_eur=2450000.0,
        risk_per_client={
            "LV-CL-001": {
                "risk_band": "medium",
                "stundung_open": True,
                "value_eur": 1250000.0,
                "signals": ["deadline_watch", "documentation_gap"],
            },
            "LV-CL-002": {
                "risk_band": "low",
                "stundung_open": False,
                "value_eur": 420000.0,
                "signals": ["complete_file"],
            },
            "LV-CL-003": {
                "risk_band": "high",
                "stundung_open": True,
                "value_eur": 780000.0,
                "signals": ["late_update", "missing_confirmation"],
            },
        },
        audit_findings=[
            {
                "code": "K17-PAV",
                "status": "ok",
                "note": "pre_action_verification_done",
            },
            {
                "code": "Q0-K0",
                "status": "ok",
                "note": "restricted_terms_absent",
            },
        ],
    )


def collect_tracker_output() -> TrackerOutput:
    if not _is_real_api_enabled():
        output = _mock_tracker_output()
        assert_no_decision_keywords(asdict(output))
        return output

    raw_path = os.environ.get("DF_163_REAL_API_JSON", "")
    if not raw_path:
        output = _mock_tracker_output()
        output.source = "mock"
        output.audit_findings.append(
            {"code": "REAL-API", "status": "skip", "note": "json_path_absent"}
        )
        assert_no_decision_keywords(asdict(output))
        return output

    path = Path(raw_path)
    if not _file_stable(path, min_age_sec=1):
        raise ValueError("input_json_not_stable")

    data = json.loads(path.read_text(encoding="utf-8"))
    output = TrackerOutput(
        iso_timestamp=iso_now(),
        source="real_api_json",
        clients_count=int(data.get("clients_count", 0)),
        stundungs_open=int(data.get("stundungs_open", 0)),
        total_value_eur=float(data.get("total_value_eur", 0.0)),
        risk_per_client=dict(data.get("risk_per_client", {})),
        audit_findings=list(data.get("audit_findings", [])),
    )
    assert_no_decision_keywords(asdict(output))
    return output


def _write_report(output: TrackerOutput) -> Path:
    reports_dir = DF_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(timezone.utc).date().isoformat()
    report_path = reports_dir / f"df-163-{date_tag}.json"

    payload = asdict(output)
    assert_no_decision_keywords(payload)

    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report_path


def main() -> int:
    locked = acquire_lock_with_identity()
    if not locked:
        return 3

    try:
        pav = k17_pre_action_verification([DF_DIR])
        if not pav.get("ok"):
            return 3

        output = collect_tracker_output()
        output.audit_findings.append(
            {
                "code": "K17-PAV",
                "status": "ok",
                "env_tag": pav.get("env_tag", "local"),
            }
        )
        assert_no_decision_keywords(asdict(output))
        _write_report(output)
        return 0
    except Exception as exc:
        err = {
            "df": "DF-163",
            "iso_timestamp": iso_now(),
            "status": "error",
            "error_type": exc.__class__.__name__,
            "message": str(exc),
        }
        try:
            assert_no_decision_keywords(err)
            reports_dir = DF_DIR / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            date_tag = datetime.now(timezone.utc).date().isoformat()
            error_path = reports_dir / f"df-163-{date_tag}-error.json"
            error_path.write_text(
                json.dumps(err, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        return 3
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())