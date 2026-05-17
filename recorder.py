"""Save / load / list step sequences as JSON files."""
import json
from datetime import date
from pathlib import Path

STEPS_DIR = Path(__file__).parent / "steps"


def _ensure_dir():
    STEPS_DIR.mkdir(parents=True, exist_ok=True)


def save_sequence(name: str, steps: list[dict]) -> str:
    """Save a step sequence. Returns the file path."""
    _ensure_dir()
    safe_name = name.replace(" ", "_").replace("/", "_")
    file_path = STEPS_DIR / f"{safe_name}.json"

    payload = {
        "name": name,
        "created_at": date.today().isoformat(),
        "steps": steps,
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(file_path)


def load_sequence(name: str) -> list[dict]:
    """Load a step sequence by name. Returns the steps list."""
    safe_name = name.replace(" ", "_").replace("/", "_")
    file_path = STEPS_DIR / f"{safe_name}.json"

    if not file_path.exists():
        # try fuzzy match
        candidates = list(STEPS_DIR.glob("*.json"))
        for c in candidates:
            payload = json.loads(c.read_text(encoding="utf-8"))
            if payload.get("name") == name:
                file_path = c
                break
        else:
            raise FileNotFoundError(f"未找到已保存的序列: {name}")

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return payload["steps"]


def list_sequences() -> list[dict]:
    """Return list of {name, created_at, file} for all saved sequences."""
    _ensure_dir()
    results = []
    for f in sorted(STEPS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        payload = json.loads(f.read_text(encoding="utf-8"))
        results.append({
            "name": payload["name"],
            "created_at": payload.get("created_at", ""),
            "steps_count": len(payload["steps"]),
            "file": f.name,
        })
    return results


def delete_sequence(name: str) -> bool:
    """Delete a saved sequence. Returns True if deleted."""
    safe_name = name.replace(" ", "_").replace("/", "_")
    file_path = STEPS_DIR / f"{safe_name}.json"
    if file_path.exists():
        file_path.unlink()
        return True
    return False
