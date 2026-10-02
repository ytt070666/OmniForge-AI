#!/usr/bin/env python3
from __future__ import annotations
import html, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from extensions.omnirag.product.release_status import build_release_status

OUT=ROOT/"artifacts/omnirag/phase7/dashboard.html"
STATUS=ROOT/"artifacts/omnirag/phase7/release_status.json"

def main():
    status=build_release_status(ROOT); STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_bytes((json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True)+"\n").encode("utf-8"))
    rows=[]
    for r in status["evaluations"]:
        rows.append(f"<tr><td>{html.escape(str(r.get('name')))}</td><td>{html.escape(str(r.get('status')))}</td><td>{html.escape(str(r.get('metric_scope')))}</td><td>{html.escape(str(r.get('path') or '—'))}</td></tr>")
    body="".join(rows) or "<tr><td colspan='4'>No evaluation records found</td></tr>"
    page=f'''<!doctype html><html><head><meta charset="utf-8"><title>OmniRAG Evaluation Status</title><style>body{{font-family:system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:8px;text-align:left}}code{{background:#eee;padding:2px 4px}}</style></head><body><h1>OmniRAG Evaluation Status</h1><p><strong>Release stage:</strong> <code>{status['release_stage']}</code></p><p><strong>Runtime verified:</strong> {str(status['runtime_verified']).lower()}</p><p>{html.escape(status['rule'])}</p><table><thead><tr><th>Evaluation</th><th>Status</th><th>Scope</th><th>Artifact</th></tr></thead><tbody>{body}</tbody></table></body></html>'''
    OUT.write_text(page, encoding="utf-8")
    print(OUT)
if __name__ == "__main__": main()
