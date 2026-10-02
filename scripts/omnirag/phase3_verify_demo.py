#!/usr/bin/env python3
"""Offline evidence-verifier sanity demo."""

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from extensions.omnirag.verifier.evidence import EvidenceItem
from extensions.omnirag.verifier.evidence_graph import verify_claims

EVIDENCE = [
    EvidenceItem("e1", "security.png", "Active Alert DNS Tunneling. Severity HIGH. Source device: Sensor-B.", "image", 0.9),
    EvidenceItem("e2", "topology.png", "Sensor-A and Sensor-B connect directly to Gateway-G7. Gateway management port: 9443.", "image", 0.8),
]

for answer in [
    "The source device is Sensor-B.",
    "The source device is Sensor-A.",
    "Gateway-G7 uses management port 9443.",
]:
    print(answer)
    print(verify_claims(answer, EVIDENCE).as_dict())
