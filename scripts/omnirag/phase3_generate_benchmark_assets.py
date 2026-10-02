#!/usr/bin/env python3
"""Generate deterministic synthetic multimodal benchmark images for Phase 3.

The assets are intentionally simple: facts needed by the questions are visible
inside figures/tables/dashboard-like images, while the paired text context is
insufficient on its own. This makes the benchmark useful for detecting whether
a true visual retrieval path contributes evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmarks" / "omnirag" / "phase3"
ASSETS = BENCH / "assets"
MANIFEST = BENCH / "visual_records.jsonl"
QUERIES = BENCH / "queries.jsonl"


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def base(title: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (1200, 760), "white")
    d = ImageDraw.Draw(img)
    d.text((50, 35), title, fill="black", font=font(34, True))
    d.line((50, 88, 1150, 88), fill="black", width=2)
    return img, d


def draw_topology(path: Path):
    img, d = base("Figure A — IoT Network Topology")
    nodes = {
        "Sensor-A": (110, 220, 330, 330),
        "Sensor-B": (110, 460, 330, 570),
        "Gateway-G7": (490, 340, 760, 460),
        "Cloud-C": (900, 340, 1110, 460),
    }
    for name, box in nodes.items():
        d.rounded_rectangle(box, radius=18, outline="black", width=4)
        d.text((box[0] + 22, box[1] + 34), name, fill="black", font=font(26, True))
    def arrow(a, b):
        d.line((*a, *b), fill="black", width=5)
        d.polygon([(b[0], b[1]), (b[0]-18, b[1]-10), (b[0]-18, b[1]+10)], fill="black")
    arrow((330, 275), (490, 390))
    arrow((330, 515), (490, 410))
    arrow((760, 400), (900, 400))
    d.text((510, 515), "Gateway management port: 9443", fill="black", font=font(25))
    img.save(path)


def draw_bar(path: Path):
    img, d = base("Figure B — Quarterly Sales (units)")
    labels = [("Q1", 72), ("Q2", 88), ("Q3", 64), ("Q4", 95)]
    x0, y0 = 120, 640
    d.line((x0, 150, x0, y0), fill="black", width=4)
    d.line((x0, y0, 1100, y0), fill="black", width=4)
    for i, (label, value) in enumerate(labels):
        x = 220 + i * 220
        h = value * 4.5
        d.rectangle((x, y0-h, x+120, y0), outline="black", width=4)
        d.text((x+27, y0+15), label, fill="black", font=font(24, True))
        d.text((x+35, y0-h-40), str(value), fill="black", font=font(28, True))
    img.save(path)


def draw_latency(path: Path):
    img, d = base("Figure C — API p95 Latency")
    points = [("10:00", 120), ("11:00", 145), ("12:00", 160), ("13:00", 190), ("14:00", 420), ("15:00", 210)]
    left, bottom, top, right = 130, 640, 150, 1100
    d.line((left, top, left, bottom), fill="black", width=4)
    d.line((left, bottom, right, bottom), fill="black", width=4)
    coords = []
    for i, (label, value) in enumerate(points):
        x = left + 80 + i*165
        y = bottom - value
        coords.append((x, y))
        d.ellipse((x-7, y-7, x+7, y+7), fill="black")
        d.text((x-35, bottom+18), label, fill="black", font=font(20))
        d.text((x-22, y-36), f"{value}ms", fill="black", font=font(18, True))
    d.line(coords, fill="black", width=5)
    img.save(path)


def draw_table(path: Path):
    img, d = base("Table D — Retrieval Ablation")
    rows = [
        ("System", "Recall@5", "MRR"),
        ("Text RAG", "78.2%", "0.71"),
        ("Hybrid RAG", "84.6%", "0.79"),
        ("OmniRAG Multimodal", "91.3%", "0.87"),
    ]
    x = [120, 650, 880, 1080]
    y0 = 170
    row_h = 105
    for r, row in enumerate(rows):
        y = y0 + r*row_h
        d.rectangle((x[0], y, x[-1], y+row_h), outline="black", width=3)
        for xx in x[1:-1]:
            d.line((xx, y, xx, y+row_h), fill="black", width=3)
        for c, text in enumerate(row):
            d.text((x[c]+18, y+31), text, fill="black", font=font(23, r == 0))
    img.save(path)


def draw_dashboard(path: Path):
    img, d = base("Security Operations Dashboard")
    d.rounded_rectangle((90, 150, 1110, 650), radius=25, outline="black", width=4)
    d.text((130, 190), "Active Alert", fill="black", font=font(26))
    d.text((130, 245), "DNS Tunneling", fill="black", font=font(42, True))
    d.text((130, 335), "Severity: HIGH", fill="black", font=font(30, True))
    d.text((130, 405), "Source device: Sensor-B", fill="black", font=font(28))
    d.text((130, 465), "Destination: 198.51.100.24", fill="black", font=font(28))
    d.text((130, 525), "First seen: 14:07 UTC", fill="black", font=font(28))
    img.save(path)


def draw_workflow(path: Path):
    img, d = base("Figure F — Agent Workflow")
    labels = ["Planner", "Retriever", "Tool Agent", "Critic", "Answer"]
    y = 340
    xs = [70, 290, 525, 760, 980]
    widths = [160, 170, 170, 160, 150]
    for i, label in enumerate(labels):
        box = (xs[i], y, xs[i]+widths[i], y+105)
        d.rounded_rectangle(box, radius=16, outline="black", width=4)
        d.text((box[0]+18, box[1]+34), label, fill="black", font=font(23, True))
        if i < len(labels)-1:
            a = (box[2], y+52)
            b = (xs[i+1], y+52)
            d.line((*a, *b), fill="black", width=4)
            d.polygon([(b[0],b[1]), (b[0]-14,b[1]-8), (b[0]-14,b[1]+8)], fill="black")
    d.text((770, 500), "Critic can request re-retrieval before Answer", fill="black", font=font(22))
    img.save(path)


def build_rows() -> tuple[list[dict], list[dict]]:
    records = [
        {"chunk_id":"mm-topology","dataset_id":"phase3-mm","document_id":"doc-topology","document_name":"01_network_topology.png","image_id":"local-01_network_topology.png","content":"Figure A shows an IoT network topology. Exact node connections and the gateway management port are visual evidence.","asset":"01_network_topology.png","doc_type":"image","metadata":{"answer_facts":["Sensor-A and Sensor-B connect to Gateway-G7","Gateway-G7 management port is 9443"]}},
        {"chunk_id":"mm-sales","dataset_id":"phase3-mm","document_id":"doc-sales","document_name":"02_sales_chart.png","image_id":"local-02_sales_chart.png","content":"Figure B is a quarterly sales chart. Values must be read from the chart.","asset":"02_sales_chart.png","doc_type":"image","metadata":{"answer_facts":["Q4 is highest at 95","Q3 is lowest at 64"]}},
        {"chunk_id":"mm-latency","dataset_id":"phase3-mm","document_id":"doc-latency","document_name":"03_latency_chart.png","image_id":"local-03_latency_chart.png","content":"Figure C plots p95 API latency over time. The peak time and value are visual evidence.","asset":"03_latency_chart.png","doc_type":"image","metadata":{"answer_facts":["14:00 is peak","peak latency is 420ms"]}},
        {"chunk_id":"mm-ablation","dataset_id":"phase3-mm","document_id":"doc-ablation","document_name":"04_ablation_table.png","image_id":"local-04_ablation_table.png","content":"Table D compares retrieval systems. Exact metrics are inside the table.","asset":"04_ablation_table.png","doc_type":"table","metadata":{"answer_facts":["OmniRAG Multimodal Recall@5 is 91.3%","OmniRAG Multimodal MRR is 0.87","Hybrid RAG Recall@5 is 84.6%"]}},
        {"chunk_id":"mm-security","dataset_id":"phase3-mm","document_id":"doc-security","document_name":"05_security_dashboard.png","image_id":"local-05_security_dashboard.png","content":"A security dashboard contains one active alert. Alert details are visible in the dashboard.","asset":"05_security_dashboard.png","doc_type":"image","metadata":{"answer_facts":["DNS Tunneling","Severity HIGH","Source Sensor-B","Destination 198.51.100.24","First seen 14:07 UTC"]}},
        {"chunk_id":"mm-workflow","dataset_id":"phase3-mm","document_id":"doc-workflow","document_name":"06_agent_workflow.png","image_id":"local-06_agent_workflow.png","content":"Figure F shows the order of components in an agent workflow and a retry note.","asset":"06_agent_workflow.png","doc_type":"image","metadata":{"answer_facts":["Planner -> Retriever -> Tool Agent -> Critic -> Answer","Critic can request re-retrieval"]}},
    ]
    queries = [
        {"id":"mm01","category":"visual_topology","question":"In Figure A, which sensors connect directly to Gateway-G7?","expected_chunk":"mm-topology","expected_markers":["Sensor-A","Sensor-B"]},
        {"id":"mm02","category":"visual_topology","question":"What management port is printed below Gateway-G7 in the topology image?","expected_chunk":"mm-topology","expected_markers":["9443"]},
        {"id":"mm03","category":"visual_chart","question":"Which quarter has the highest sales in Figure B?","expected_chunk":"mm-sales","expected_markers":["Q4","95"]},
        {"id":"mm04","category":"visual_chart","question":"What is the Q3 sales value shown on the chart?","expected_chunk":"mm-sales","expected_markers":["64"]},
        {"id":"mm05","category":"visual_chart","question":"At what time does the p95 latency peak in Figure C?","expected_chunk":"mm-latency","expected_markers":["14:00","420ms"]},
        {"id":"mm06","category":"visual_table","question":"What Recall@5 does OmniRAG Multimodal achieve in Table D?","expected_chunk":"mm-ablation","expected_markers":["91.3%"]},
        {"id":"mm07","category":"visual_table","question":"Compare Hybrid RAG and OmniRAG Multimodal Recall@5 from the table.","expected_chunk":"mm-ablation","expected_markers":["84.6%","91.3%"]},
        {"id":"mm08","category":"visual_dashboard","question":"What is the active security alert shown in the dashboard?","expected_chunk":"mm-security","expected_markers":["DNS Tunneling"]},
        {"id":"mm09","category":"visual_dashboard","question":"Which device is the source of the HIGH severity alert?","expected_chunk":"mm-security","expected_markers":["Sensor-B"]},
        {"id":"mm10","category":"visual_dashboard","question":"What destination IP is visible for the alert?","expected_chunk":"mm-security","expected_markers":["198.51.100.24"]},
        {"id":"mm11","category":"visual_workflow","question":"In Figure F, which component comes immediately after Tool Agent?","expected_chunk":"mm-workflow","expected_markers":["Critic"]},
        {"id":"mm12","category":"visual_workflow","question":"What can the Critic request before the Answer stage?","expected_chunk":"mm-workflow","expected_markers":["re-retrieval"]},
        {"id":"mm13","category":"crosslingual_visual","question":"图B中销量最高的是哪个季度？","expected_chunk":"mm-sales","expected_markers":["Q4","95"]},
        {"id":"mm14","category":"crosslingual_visual","question":"安全看板中的告警源设备是什么？","expected_chunk":"mm-security","expected_markers":["Sensor-B"]},
        {"id":"mm15","category":"crosslingual_visual","question":"图F中 Tool Agent 后面的节点是什么？","expected_chunk":"mm-workflow","expected_markers":["Critic"]},
        {"id":"mm16","category":"mixed_evidence","question":"Which benchmark system has both the best Recall@5 and MRR?","expected_chunk":"mm-ablation","expected_markers":["OmniRAG Multimodal","91.3%","0.87"]},
        {"id":"mm17","category":"mixed_evidence","question":"Which sensor in the topology is also named as the source device on the security dashboard?","expected_chunks":["mm-topology","mm-security"],"expected_markers":["Sensor-B"]},
        {"id":"mm18","category":"mixed_evidence","question":"The dashboard first sees the alert at what time, and what is the latency chart's peak time?","expected_chunks":["mm-security","mm-latency"],"expected_markers":["14:07 UTC","14:00"]},
    ]
    return records, queries


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    draw_topology(ASSETS / "01_network_topology.png")
    draw_bar(ASSETS / "02_sales_chart.png")
    draw_latency(ASSETS / "03_latency_chart.png")
    draw_table(ASSETS / "04_ablation_table.png")
    draw_dashboard(ASSETS / "05_security_dashboard.png")
    draw_workflow(ASSETS / "06_agent_workflow.png")
    records, queries = build_rows()
    MANIFEST.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in records) + "\n", encoding="utf-8")
    QUERIES.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in queries) + "\n", encoding="utf-8")
    print(f"Generated {len(records)} visual records and {len(queries)} queries under {BENCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
