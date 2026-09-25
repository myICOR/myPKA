# Vex's verify.py, run against the FIXED updater (step 13). verify.py swaps
# his proposed writer into the step 12 updater; since R2 that writer IS the
# updater's write_atomic (signature (src, root, rel)), so there is nothing to
# swap: the same three scenarios run on the updater as it ships.
# Run from this folder: python3 verify-fixed.py
import importlib.util
from h import *
spec = importlib.util.spec_from_file_location("up", UP); up = importlib.util.module_from_spec(spec); spec.loader.exec_module(up)
main = up.main
# P4: a folder swapped for a symlink between plan and write
W = Path("v4"); shutil.rmtree(W, ignore_errors=True); T = W/"mypka"; T.mkdir(parents=True); O = W/"OUTSIDE"; O.mkdir()
installed(T, "mypka", "1.0.0", {"AGENTS.md": "a\n", "06 AI Team/Scripts/x.py": "old\n"})
R = release(W/"rel", "mypka", "1.1.0", {"AGENTS.md": "b\n", "06 AI Team/Scripts/x.py": "new\n"})
rp = up.plan
def racing(args):
    out = rp(args); shutil.rmtree(T/"06 AI Team"); os.symlink(O.resolve(), T/"06 AI Team"); return out
up.plan = racing
print("P4 exit", main(["x", "--release", str(R), "--target", str(T), "--live"]))
print("P4 OUTSIDE:", [str(p.relative_to(O)) for p in O.rglob("*")])
up.plan = rp
# P6: the release manifest is not listed in files, and the target's .mypka is a symlink
W = Path("v6"); shutil.rmtree(W, ignore_errors=True); T = W/"mypka"; T.mkdir(parents=True); O = W/"OUTSIDE"; O.mkdir()
(T/"AGENTS.md").write_text("a\n"); os.symlink(O.resolve(), T/".mypka")
R = mk(W/"rel", {"AGENTS.md": "b\n"}); (R/".mypka").mkdir(); (R/".mypka/manifest.json").write_text(json.dumps({"version": "1.1.0", "files": {"AGENTS.md": sha(b"b\n")}}))
print("P6 exit", main(["x", "--release", str(R), "--target", str(T), "--live"]))
print("P6 OUTSIDE:", os.listdir(O))
# clean control: a normal update still applies, a new nested folder is created
W = Path("v0"); shutil.rmtree(W, ignore_errors=True); T = W/"mypka"; T.mkdir(parents=True)
installed(T, "mypka", "1.0.0", {"AGENTS.md": "a\n"})
R = release(W/"rel", "mypka", "1.1.0", {"AGENTS.md": "b\n", "06 AI Team/new/dir/f.md": "n\n"})
print("control exit", main(["x", "--release", str(R), "--target", str(T), "--live"]), (T/"AGENTS.md").read_text().strip(),
      (T/"06 AI Team/new/dir/f.md").exists())
