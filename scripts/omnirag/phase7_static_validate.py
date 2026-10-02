#!/usr/bin/env python3
from __future__ import annotations
import os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "deploy/omnirag/Dockerfile",
    "deploy/omnirag/docker/docker-compose.omnirag.yml",
    "deploy/omnirag/k8s/kustomization.yaml",
    ".github/workflows/omnirag-ci.yml",
    "config/omnirag/phase7/omnirag.env.example",
    "scripts/omnirag/phase7_build_dashboard.py",
]
PHASE7_DOCS = [
    ROOT / "docs/omnirag/PHASE7_ENGINEERING_PRODUCTIZATION.md",
    ROOT / "docs/omnirag/PHASE7_LOCAL_RUN_LATER.md",
    ROOT / "docs/omnirag/PORTFOLIO_README.md",
]
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|password|secret)\s*[=:]\s*['\"]?(?!REPLACE|\$\{|\{\{|$)[A-Za-z0-9_\-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

def run(*cmd: str) -> None:
    env = os.environ.copy()
    if cmd[0] == "bash":
        # CreateProcess searches Windows system directories before PATH. Resolve
        # Git Bash explicitly so an installed WSL shim does not intercept it.
        bash = shutil.which("bash")
        if not bash:
            raise RuntimeError("bash is required for Phase-5 static validation")
        cmd = (bash, *cmd[1:])
        if os.name == "nt" and sys.prefix != sys.base_prefix:
            python3 = Path(sys.executable).with_name("python3.exe")
            if not python3.exists():
                shutil.copyfile(sys.executable, python3)
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)

def main() -> None:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        raise SystemExit("missing required phase7 files: " + ", ".join(missing))

    run(sys.executable, "-m", "compileall", "-q", "extensions/omnirag", "scripts/omnirag")
    run(sys.executable, "scripts/omnirag/phase1_verify_core_untouched.py")
    run(sys.executable, "scripts/omnirag/phase7_verify_runtime_source.py", ".", "--mode", "prepatch")
    run("bash", "scripts/omnirag/phase5_static_validate.sh")
    run(sys.executable, "scripts/omnirag/phase7_build_dashboard.py")

    # Parse Phase-7 YAML syntax. Semantic runtime validation remains deferred.
    import yaml
    yaml_files = list((ROOT / "deploy/omnirag").rglob("*.yaml")) + list((ROOT / "deploy/omnirag").rglob("*.yml")) + [ROOT / ".github/workflows/omnirag-ci.yml"]
    for yml in yaml_files:
        with yml.open("r", encoding="utf-8") as fh:
            list(yaml.safe_load_all(fh))

    scan_files: list[Path] = []
    for base in [ROOT / "deploy/omnirag", ROOT / "config/omnirag/phase7"]:
        scan_files.extend(p for p in base.rglob("*") if p.is_file())
    scan_files.extend(PHASE7_DOCS)
    bad: list[str] = []
    for p in scan_files:
        if p.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".example", ""}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                bad.append(str(p.relative_to(ROOT)))
    if bad:
        raise SystemExit("potential committed secret material: " + ", ".join(sorted(set(bad))))

    print("Phase-7 static validation: PASS")

if __name__ == "__main__":
    main()
