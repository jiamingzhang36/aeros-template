#!/usr/bin/env python3
from pathlib import Path
import json, os, shutil, subprocess, sys, tempfile
ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aeros_package_e2e_") as name:
        base=Path(name); venv=base/"venv"; project=base/"project"; source=base/"source"; project.mkdir(); source.mkdir()
        shutil.copy2(ROOT/"pyproject.toml", source/"pyproject.toml")
        shutil.copytree(ROOT/"aeros", source/"aeros")
        (project/"project_manifest.yml").write_text("project:\n  name: package_e2e\n",encoding="utf-8")
        wheels=base/"wheels"; wheels.mkdir()
        candidates=[
            os.environ.get("AEROS_BUILD_PYTHON", ""),
            sys.executable,
            shutil.which("python3.13") or "", shutil.which("python3.12") or "",
            shutil.which("python3.11") or "", shutil.which("python3.10") or "",
            "/Users/jiamingzhang/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
            "/Users/jiamingzhang/opt/anaconda3/bin/python",
        ]
        build_python=""
        for candidate in candidates:
            probe = subprocess.run(
                [candidate, "-c", "import sys,setuptools.build_meta,yaml; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"],
                capture_output=True,
            ) if candidate and Path(candidate).is_file() else None
            if probe is not None and probe.returncode == 0:
                build_python=candidate; break
        if not build_python: print("FAIL: no local Python with setuptools.build_meta; set AEROS_BUILD_PYTHON"); return 1
        build=subprocess.run([build_python,"-m","pip","wheel","--no-deps","--no-build-isolation","--wheel-dir",str(wheels),str(source)],capture_output=True,text=True,timeout=120)
        if build.returncode!=0: print("FAIL: local wheel build",build.stderr); return 1
        wheel_files=list(wheels.glob("aeros_runtime-*.whl"))
        if len(wheel_files)!=1: print("FAIL: expected exactly one AEROS wheel"); return 1
        venv_python = sys.executable if sys.version_info >= (3, 10) else build_python
        create=subprocess.run([venv_python,"-m","venv","--system-site-packages",str(venv)],capture_output=True,text=True)
        if create.returncode!=0: print("FAIL: venv creation",create.stderr); return 1
        py=venv/"bin/python"; pip=venv/"bin/pip"
        install=subprocess.run([str(pip),"install","--no-deps",str(wheel_files[0])],capture_output=True,text=True,timeout=120)
        if install.returncode!=0: print("FAIL: local package install",install.stderr); return 1
        env=dict(os.environ); env.pop("PYTHONPATH",None)
        prep=subprocess.run([str(py),"-m","aeros.cli","migrate","prepare"],cwd=project,env=env,capture_output=True,text=True)
        doctor=subprocess.run([str(py),"-m","aeros.cli","doctor","--json"],cwd=project,env=env,capture_output=True,text=True)
        failures=[]
        if prep.returncode!=0: failures.append("package-mode prepare failed: "+(prep.stderr or prep.stdout))
        if doctor.returncode!=0: failures.append("package-mode doctor failed: "+(doctor.stderr or doctor.stdout))
        try: report=json.loads(doctor.stdout)
        except Exception: report={}; failures.append("doctor did not emit JSON")
        if report.get("status")!="PASS": failures.append(f"doctor status is not PASS: {report}")
        if any((project/name).exists() for name in ("aeros","checks","harness","templates","tools","tests")): failures.append("package-mode fixture unexpectedly contains vendored runtime surfaces")
        if not (project/".aeros/project.yml").exists() or not (project/"aeros.lock").exists(): failures.append("package-mode project/lock files missing")
        if failures: print("FAIL: de-vendor package E2E"); [print(f"- {x}") for x in failures]; return 1
    print("PASS: locally installed AEROS runs package-mode project without vendored runtime surfaces"); return 0
if __name__=="__main__": raise SystemExit(main())
