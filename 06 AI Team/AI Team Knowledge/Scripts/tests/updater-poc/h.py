import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
UP = str(Path(__file__).resolve().parents[2] / "mypka-update.py")  # the lab left the Desktop; no absolute path
PY = "/opt/homebrew/bin/python3.12"
def sha(b): return hashlib.sha256(b).hexdigest()
def mk(root, files):
    root = Path(root); shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    for rel, body in files.items():
        p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(body if isinstance(body, bytes) else body.encode())
    return root
def release(root, product, version, files, previous=None, seed=None):
    meta = {"mypka": ".mypka", "icor": ".icor-for-life"}[product]
    r = mk(root, files)
    man = {"name": product, "version": version, "files": {k: sha((v if isinstance(v, bytes) else v.encode())) for k, v in files.items()},
           "previous": previous or {}, "seed": seed or []}
    man["files"][meta + "/manifest.json"] = "self"
    (r / meta).mkdir(parents=True, exist_ok=True); (r / meta / "manifest.json").write_text(json.dumps(man))
    return r
def installed(target, product, version, files):
    meta = {"mypka": ".mypka", "icor": ".icor-for-life"}[product]
    t = Path(target); (t / meta).mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        p = t / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(body)
    man = {"name": product, "version": version, "files": {k: sha(v.encode()) for k, v in files.items()}}
    man["files"][meta + "/manifest.json"] = "self"
    (t / meta / "manifest.json").write_text(json.dumps(man))
def run(rel, target, product="mypka", live=True, extra=()):
    cmd = [PY, UP, "--release", str(rel), "--target", str(target), "--product", product] + (["--live"] if live else []) + list(extra)
    r = subprocess.run(cmd, capture_output=True, text=True)
    print("exit", r.returncode); print((r.stdout + r.stderr).strip()[:1500])
    return r
