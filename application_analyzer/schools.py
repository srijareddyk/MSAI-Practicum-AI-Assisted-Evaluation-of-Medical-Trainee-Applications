"""Load school lists and match extracted institution strings."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def _default_config_path() -> Path:
    return Path(__file__).resolve().parent / "config" / "school_lists.yaml"


def load_school_lists(path: Path | None = None) -> dict[str, Any]:
    p = path or _default_config_path()
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalize_institution(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s&./'-]", "", s)
    return s


def is_top_school(candidate: str | None, top_list: list[str]) -> bool:
    if not candidate:
        return False
    cn = normalize_institution(candidate)
    if len(cn) < 4:
        return False
    for school in top_list:
        sn = normalize_institution(school)
        if sn and sn in cn:
            return True
        if cn in sn and len(cn) >= 10:
            return True
    return False
