"""version_info.py — reads local version.json."""
import json
from pathlib import Path

_VF = Path(__file__).parent / "version.json"


def get_local_version() -> str:
    try:
        return json.loads(_VF.read_text()).get("version", "unknown")
    except Exception:
        return "unknown"
