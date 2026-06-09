import json
import os
from datetime import date

_QUOTA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".quota.json")
DAILY_LIMIT = 1500
_WARN_AT = int(DAILY_LIMIT * 0.8)


def _load() -> dict:
    if os.path.exists(_QUOTA_FILE):
        with open(_QUOTA_FILE) as f:
            data = json.load(f)
        if data.get("date") == str(date.today()):
            return data
    return {"date": str(date.today()), "count": 0}


def _save(data: dict) -> None:
    with open(_QUOTA_FILE, "w") as f:
        json.dump(data, f)


def track(n: int = 1) -> int:
    data = _load()
    data["count"] += n
    _save(data)
    used = data["count"]
    if used >= DAILY_LIMIT:
        raise RuntimeError(
            f"[QUOTA] Limite diário atingido: {used}/{DAILY_LIMIT}. "
            "Aguarde o reset às 00h00 (horário do Google)."
        )
    if used >= _WARN_AT:
        print(f"[QUOTA] Aviso: {used}/{DAILY_LIMIT} requisições hoje ({used * 100 // DAILY_LIMIT}%)")
    return used


def status() -> None:
    data = _load()
    used = data["count"]
    print(f"[QUOTA] {used}/{DAILY_LIMIT} requisições usadas hoje ({used * 100 // DAILY_LIMIT}%)")
