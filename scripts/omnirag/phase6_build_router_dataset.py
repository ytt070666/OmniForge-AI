#!/usr/bin/env python3
"""Build a leakage-controlled synthetic training set plus protected benchmarks.

No external model is used to generate the data. The source is deterministic
human-authored templates with explicit lineage. Existing Phase-1/3/5 benchmark
questions are protected evaluation only and never copied into train/validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extensions.omnirag.training.dataset import assert_no_leakage, leakage_report, max_ngram_overlap, write_jsonl
from extensions.omnirag.training.schema import RouterExample, make_completion
from extensions.omnirag.training.redaction import findings

OUT = ROOT / "benchmarks/omnirag/phase6/router"
SEED = 20260917

SLOTS = {
    "ids": ["QX-741", "NODE-88A", "SRV-2049", "ALPHA-27", "GW-013", "CASE-771"],
    "ports": ["9443", "18443", "8088", "7443", "31090", "12001"],
    "topics": ["battery peak shifting", "agent long-term memory", "cross-modal retrieval", "contract renewal", "network anomaly detection", "privacy-preserving search"],
    "concepts": ["why hybrid retrieval helps", "how episodic memory supports planning", "why reranking changes relevance", "how evidence verification reduces hallucination", "how batteries reduce peak load", "how multimodal fusion combines evidence"],
    "figures": ["Figure A", "the latency chart", "the topology diagram", "the ablation table", "the security dashboard", "the workflow image"],
    "entities": ["Gateway-G7", "Sensor-A", "Q4", "p95 latency", "Recall@5", "Agent Supervisor"],
    "cities": ["Tokyo", "Osaka", "Kyoto", "Nagoya", "Fukuoka", "Sapporo"],
    "times": ["tomorrow", "this afternoon", "Saturday", "next Monday", "tonight", "this weekend"],
    "totals": ["1000", "720", "1440", "600", "480", "2880"],
    "downtimes": ["25", "18", "42", "12", "9", "73"],
}

# Families are the split unit. No family appears in more than one split.
TEMPLATES = {
    "lexical_precision": {
        "train": [
            "Find the exact record containing {id}.",
            "Which document lists identifier {id}?",
            "Return the configured service port {port} for the named gateway.",
            "Locate the entry with exact code {id} and report where it appears.",
        ],
        "validation": ["Search for the literal maintenance token {id} without paraphrasing it."],
        "test": ["Which source contains the precise string {id}?"],
    },
    "semantic": {
        "train": [
            "Explain {concept} in plain language.",
            "What is the underlying idea behind {topic}?",
            "Describe the mechanism of {concept} even if the source uses different wording.",
            "I need the passage that conceptually explains {topic}, not an exact keyword match.",
        ],
        "validation": ["Which source best explains {concept} using semantically similar language?"],
        "test": ["Find information that means the same thing as: {concept}."],
    },
    "hybrid": {
        "train": [
            "For device {id}, explain the purpose of port {port} and its operational context.",
            "Find {id}, then summarize what the document says about {topic} around it.",
            "Use both the exact token {id} and the surrounding meaning to answer about {topic}.",
            "Locate port {port} and explain why it matters for {topic}.",
        ],
        "validation": ["Match exact identifier {id} while also interpreting its relation to {topic}."],
        "test": ["Use the literal code {id} plus semantic context about {topic}."],
    },
    "crosslingual": {
        "train": [
            "请在英文资料中查找并解释：{concept}。",
            "用中文回答，资料可能是英文：{topic} 的核心机制是什么？",
            "检索英文知识库，说明 {concept}。",
            "问题是中文但语料是英文，请找到关于 {topic} 的相关内容。",
        ],
        "validation": ["请跨语言检索英文文档：{concept} 是如何工作的？"],
        "test": ["中文提问、英文资料：请解释 {topic}。"],
    },
    "visual": {
        "train": [
            "In {figure}, what value or label is shown for {entity}?",
            "Inspect {figure} and identify the item connected to {entity}.",
            "Read the visual evidence in {figure}; which element corresponds to {entity}?",
            "Do not rely on caption text alone: inspect {figure} for {entity}.",
        ],
        "validation": ["From {figure}, read the displayed information associated with {entity}."],
        "test": ["Look at {figure} itself and answer the question about {entity}."],
    },
    "tool": {
        "train": [
            "Search the knowledge base for {topic}.",
            "Use the weather service to report conditions in {city} for {time_ref}.",
            "Look up device {id} in the asset catalog.",
            "Search the runbook for {topic} failure recovery.",
            "Calculate service availability if total minutes are {total} and downtime is {downtime}.",
            "查询知识库中关于 {topic} 的资料。",
            "查询设备 {id} 的资产信息。",
            "查找 {topic} 故障排查手册。",
        ],
        "validation": [
            "Use the appropriate enterprise tool to retrieve the asset record for {id}.",
            "用工具查询 {city} {time_ref} 的天气。",
            "计算总时长 {total} 分钟、停机 {downtime} 分钟时的可用率。",
        ],
        "test": [
            "Please use the runbook tool to find remediation guidance for {topic}.",
            "使用企业知识检索工具查找 {topic}。",
            "查询资产目录中的设备 {id}。",
        ],
    },
}


def completion_for(kind: str, query: str) -> str:
    if kind == "lexical_precision":
        return make_completion(query_class=kind, retrieval_profile="sparse_heavy", evidence_strictness="high")
    if kind == "semantic":
        return make_completion(query_class=kind, retrieval_profile="dense_heavy")
    if kind == "hybrid":
        return make_completion(query_class=kind, retrieval_profile="balanced", evidence_strictness="high")
    if kind == "crosslingual":
        return make_completion(query_class=kind, retrieval_profile="dense_heavy")
    if kind == "visual":
        return make_completion(query_class=kind, retrieval_profile="balanced", needs_visual=True, evidence_strictness="high")
    if kind == "tool":
        q = query.lower()
        if "weather" in q or "天气" in q:
            intent = "weather"
        elif "asset" in q or "资产" in q or "device" in q or "设备" in q:
            intent = "device_lookup"
        elif "runbook" in q or "排查手册" in q or "remediation" in q:
            intent = "runbook_search"
        elif "availability" in q or "可用率" in q:
            intent = "availability_calc"
        else:
            intent = "knowledge_search"
        return make_completion(
            query_class=kind,
            retrieval_profile="balanced",
            needs_tools=True,
            tool_intent=intent,
            evidence_strictness="high",
        )
    raise KeyError(kind)


def fill(template: str, i: int) -> str:
    return template.format(
        id=SLOTS["ids"][i % len(SLOTS["ids"])],
        port=SLOTS["ports"][(i + 1) % len(SLOTS["ports"])],
        topic=SLOTS["topics"][(i + 2) % len(SLOTS["topics"])],
        concept=SLOTS["concepts"][(i + 1) % len(SLOTS["concepts"])],
        figure=SLOTS["figures"][(i + 3) % len(SLOTS["figures"])],
        entity=SLOTS["entities"][(i + 2) % len(SLOTS["entities"])],
        city=SLOTS["cities"][(i + 1) % len(SLOTS["cities"])],
        time_ref=SLOTS["times"][(i + 2) % len(SLOTS["times"])],
        total=SLOTS["totals"][(i + 4) % len(SLOTS["totals"])],
        downtime=SLOTS["downtimes"][(i + 1) % len(SLOTS["downtimes"])],
    )


def build_synthetic() -> dict[str, list[dict]]:
    rng = random.Random(SEED)
    splits = {"train": [], "validation": [], "test": []}
    per_family = {"train": 6, "validation": 6, "test": 6}
    seq = 0
    for kind, by_split in TEMPLATES.items():
        for split, templates in by_split.items():
            for family_index, template in enumerate(templates):
                family_id = f"{kind}-{split}-family-{family_index:02d}"
                queries = [fill(template, i + family_index * 11) for i in range(per_family[split])]
                # Stable shuffle avoids the output looking grouped while retaining reproducibility.
                rng.shuffle(queries)
                for query in queries:
                    seq += 1
                    language = "zh" if any("\u4e00" <= c <= "\u9fff" for c in query) else "en"
                    item = RouterExample(
                        id=f"syn-{seq:04d}",
                        family_id=family_id,
                        source_type="synthetic_template",
                        query=query,
                        completion=completion_for(kind, query),
                        language=language,
                    )
                    splits[split].append(item.as_record())
    return splits


def protected_record(pid: str, family: str, query: str, completion: str, source_ref: str) -> dict:
    language = "zh" if any("\u4e00" <= c <= "\u9fff" for c in query) else "en"
    return RouterExample(
        id=pid,
        family_id=family,
        source_type="protected_benchmark",
        source_ref=source_ref,
        query=query,
        completion=completion,
        language=language,
    ).as_record()


def build_protected() -> list[dict]:
    rows: list[dict] = []
    p1 = ROOT / "benchmarks/omnirag/phase1/queries.jsonl"
    for line in p1.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        cat = r["category"]
        if cat == "lexical":
            completion = completion_for("lexical_precision", r["question"])
        elif cat == "hybrid":
            completion = completion_for("hybrid", r["question"])
        elif cat == "crosslingual":
            completion = completion_for("crosslingual", r["question"])
        else:
            # memory/mcp/multimodal here are conceptual text questions, not actual
            # tool invocations or pixel-grounded visual questions.
            completion = completion_for("semantic", r["question"])
        rows.append(protected_record(f"p1-{r['id']}", f"protected-p1-{cat}", r["question"], completion, str(p1.relative_to(ROOT))))

    p3 = ROOT / "benchmarks/omnirag/phase3/queries.jsonl"
    for line in p3.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows.append(
            protected_record(
                f"p3-{r['id']}",
                f"protected-p3-{r['category']}",
                r["question"],
                completion_for("visual", r["question"]),
                str(p3.relative_to(ROOT)),
            )
        )

    p5 = ROOT / "benchmarks/omnirag/phase5/tool_selection_cases.jsonl"
    tool_map = {
        "search_docs_0": "knowledge_search",
        "weather_1": "weather",
        "lookup_device_2": "device_lookup",
        "search_runbook_3": "runbook_search",
        "availability_4": "availability_calc",
    }
    for idx, line in enumerate(p5.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        intent = tool_map[r["expected"]]
        completion = make_completion(
            query_class="tool",
            retrieval_profile="balanced",
            needs_tools=True,
            tool_intent=intent,
            evidence_strictness="high",
        )
        rows.append(protected_record(f"p5-{idx:02d}", f"protected-p5-{intent}", r["query"], completion, str(p5.relative_to(ROOT))))
    return rows


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(OUT))
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    splits = build_synthetic()
    protected = build_protected()
    report = leakage_report(splits, protected)
    assert_no_leakage(report)
    protected_overlap = [max_ngram_overlap(splits["train"], row, n=5) for row in protected]
    report["protected_train_max_5gram_overlap"] = max(protected_overlap, default=0.0)
    if report["protected_train_max_5gram_overlap"] > 0.60:
        raise SystemExit("protected benchmark has excessive 5-gram overlap with training templates")

    # Dataset hygiene is fail-closed for secret-like material. IP fixtures are
    # reported but not generated by this Phase-6 template set.
    secret_kinds = {"email", "bearer", "api_key", "private_key"}
    hygiene = []
    for name, rows in {**splits, "protected": protected}.items():
        for row in rows:
            found = [f.kind for f in findings(row["query"])]
            dangerous = sorted(set(found) & secret_kinds)
            if dangerous:
                raise SystemExit(f"secret-like data in {name}/{row['id']}: {dangerous}")
            if found:
                hygiene.append({"split": name, "id": row["id"], "finding_kinds": sorted(set(found))})

    for name, rows in splits.items():
        write_jsonl(out / f"{name}.jsonl", rows)
    write_jsonl(out / "protected_benchmark.jsonl", protected)

    manifest = {
        "schema_version": 1,
        "seed": SEED,
        "generator": "human-authored deterministic templates; no LLM generation",
        "split_unit": "family_id",
        "protected_sources_used_for_training": False,
        "leakage_report": report,
        "hygiene_findings": hygiene,
        "files": {},
    }
    for name in ["train", "validation", "test", "protected_benchmark"]:
        path = out / f"{name}.jsonl"
        manifest["files"][path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    (out / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["counts"], "class_counts": report["class_counts"]}, ensure_ascii=False, indent=2))
    print("PASS: Phase-6 router dataset built with family-level split and protected benchmark isolation")


if __name__ == "__main__":
    main()
