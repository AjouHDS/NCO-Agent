from __future__ import annotations
import hashlib
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any
import requests


API = "https://api.fda.gov/drug/label.json"
API_KEY = os.environ.get("OPENFDA_API_KEY")
MAX_SKIP = 25_000
PAGE = 100
ADVERSE_FIELDS = [
    "boxed_warning",
    "adverse_reactions",
    "warnings_and_precautions",
    "warnings",
]
PROFILE_FIELDS = [
    "indications_and_usage",
    "mechanism_of_action",
    "contraindications",
]
# mechanism_of_action이 비었을 때 참고용 (자동 대체하지 않고 별도 보관)
FALLBACK_FIELDS = ["clinical_pharmacology"]
ALL_TEXT_FIELDS = ADVERSE_FIELDS + PROFILE_FIELDS + FALLBACK_FIELDS
PHARM_CLASS = {
    "epc": "pharm_class_epc",   
    "moa": "pharm_class_moa",
    "pe": "pharm_class_pe",   
    "cs": "pharm_class_cs",  
}


class OpenFDAClient:
    def __init__(self, api_key: str | None = API_KEY, min_interval: float = 0.3):
        self.api_key = api_key
        self.min_interval = min_interval
        self._last = 0.0
        self.session = requests.Session()

    def _throttle(self) -> None:
        gap = time.time() - self._last
        if gap < self.min_interval:
            time.sleep(self.min_interval - gap)
        self._last = time.time()

    def get(self, params: dict) -> dict | None:
        if self.api_key:
            params = {**params, "api_key": self.api_key}

        for attempt in range(4):
            self._throttle()
            try:
                r = self.session.get(API, params=params, timeout=60)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue

            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                wait = 60 if not self.api_key else 5
                print(f"  [429] 레이트 리밋 — {wait}초 대기"
                      f"{' (키 없이 실행 중: 하루 1,000건)' if not self.api_key else ''}")
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")

        raise RuntimeError("재시도 초과")


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def _strip_class_tag(s: str) -> str:
    return re.sub(r"\s*\[(EPC|MoA|PE|CS)\]\s*$", "", s).strip()


def _collect_texts(labels: list[dict], field: str) -> list[dict]:
    by_hash: dict[str, str] = {}
    counts: Counter = Counter()

    for lab in labels:
        val = lab.get(field)
        chunks = val if isinstance(val, list) else ([val] if isinstance(val, str) else [])
        seen_here = set()
        for c in chunks:
            if not isinstance(c, str) or not c.strip():
                continue
            h = hashlib.md5(_norm(c).encode()).hexdigest()
            by_hash.setdefault(h, c.strip())
            if h not in seen_here:
                counts[h] += 1
                seen_here.add(h)

    return [
        {"text": by_hash[h], "label_count": n}
        for h, n in counts.most_common()
    ]


def _uniq(labels: list[dict], path: str) -> list[str]:
    out: list[str] = []
    seen = set()
    for lab in labels:
        for v in (lab.get("openfda", {}) or {}).get(path, []) or []:
            if v not in seen:
                seen.add(v)
                out.append(v)
    return out


def build_query(ingredient: str) -> str:
    t = ingredient.replace('"', '\\"')
    return f'(openfda.substance_name:"{t}" OR openfda.generic_name:"{t}")'


def fetch(client: OpenFDAClient, ingredient: str, max_labels: int = 1000) -> dict:
    q = build_query(ingredient)
    now = datetime.now(timezone.utc).isoformat()

    first = client.get({"search": q, "limit": 1})

    if first is None:
        return {
            "query": ingredient,
            "found": False,
            "not_marketed_us": True,
            "label_count": 0,
            "drug_info": None,
            "retrieved_at": now,
        }

    total = int(first["meta"]["results"]["total"])
    target = min(total, max_labels, MAX_SKIP)

    labels: list[dict] = []
    while len(labels) < target:
        page = client.get({"search": q, "limit": min(PAGE, target - len(labels)),
                           "skip": len(labels)})
        if not page or not page.get("results"):
            break
        labels.extend(page["results"])

    drug_class = {
        k: [_strip_class_tag(v) for v in _uniq(labels, f)]
        for k, f in PHARM_CLASS.items()
    }

    return {
        "query": ingredient,
        "found": True,
        "not_marketed_us": False,
        "label_count": total,
        "labels_fetched": len(labels),

        "drug_info": {
            "drug_name": ingredient,
            "indications": _collect_texts(labels, "indications_and_usage"),
            "mechanism_of_action": _collect_texts(labels, "mechanism_of_action"),
            "contraindications": _collect_texts(labels, "contraindications"),
            "adverse_effects": {
                f: _collect_texts(labels, f) for f in ADVERSE_FIELDS
            },
            "_fallback": {
                f: _collect_texts(labels, f) for f in FALLBACK_FIELDS
            },
        },

    }


def collect(ingredients: list[str], max_labels: int = 1000) -> list[dict]:
    client = OpenFDAClient()
    if not API_KEY:
        print("⚠  OPENFDA_API_KEY not set\n")

    out = []
    for i, ing in enumerate(ingredients, 1):
        r = fetch(client, ing, max_labels=max_labels)
        out.append(r)

    return out

    
if __name__ == "__main__":
    targets = ["warfarin"]
    results = collect(targets)