"""Provider-neutral semantic judge contract for the later local model run.

The deterministic verifier remains the Phase-3 first layer. This helper makes
it straightforward to add a Qwen/VLM judge only for ambiguous claims without
coupling the extension to one SDK.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Callable


@dataclass(frozen=True)
class SemanticJudgement:
    support_score: float
    conflict: bool
    rationale: str

    def as_dict(self) -> dict:
        return asdict(self)


def build_prompt(claim: str, evidence: str) -> str:
    return f"""You are a strict evidence verifier. Judge only whether the evidence supports the claim.
Return JSON only with keys support_score (0..1), conflict (boolean), rationale (short string).
Do not use outside knowledge.
CLAIM:\n{claim}\n\nEVIDENCE:\n{evidence}\n"""


def parse_judgement(raw: str) -> SemanticJudgement:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    obj = json.loads(text)
    score = max(0.0, min(1.0, float(obj["support_score"])))
    return SemanticJudgement(score, bool(obj["conflict"]), str(obj.get("rationale", ""))[:500])


def judge(claim: str, evidence: str, invoke: Callable[[str], str]) -> SemanticJudgement:
    return parse_judgement(invoke(build_prompt(claim, evidence)))
