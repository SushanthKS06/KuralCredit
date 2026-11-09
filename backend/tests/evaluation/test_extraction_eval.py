from __future__ import annotations

import json
from pathlib import Path

from app.domain.number_normalizer import find_amounts

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "backend" / "app" / "fixtures" / "evaluation_utterances.jsonl"


def test_extraction_evaluation_corpus():
    assert FIXTURES.exists(), "Evaluation corpus must exist"
    records = []
    with FIXTURES.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    assert len(records) >= 5
    for item in records:
        if "expected_facts" in item:
            amounts = find_amounts(item["text"])
            assert amounts or item.get("category") == "tamil_script_amounts"
