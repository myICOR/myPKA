# P4: TOCTOU. plan() checks every component for symlinks; the writes happen later and only re-check the leaf.
# Simulate a concurrent process (a sync client, another tool) swapping a folder for a symlink between plan and write.
import importlib.util
from h import *
W = Path("w4"); shutil.rmtree(W, ignore_errors=True); T = W/"mypka"; T.mkdir(parents=True); O = W/"OUTSIDE"; O.mkdir()
installed(T, "mypka", "1.0.0", {"AGENTS.md": "a\n", "06 AI Team/Scripts/x.py": "old\n"})
R = release(W/"rel", "mypka", "1.1.0", {"AGENTS.md": "b\n", "06 AI Team/Scripts/x.py": "new\n"}, previous={})
spec = importlib.util.spec_from_file_location("up", UP); up = importlib.util.module_from_spec(spec); spec.loader.exec_module(up)
real_plan = up.plan
def racing_plan(args):
    out = real_plan(args)
    shutil.rmtree(T/"06 AI Team"); os.symlink(O.resolve(), T/"06 AI Team")   # the race window
    return out
up.plan = racing_plan
rc = up.main(["x", "--release", str(R), "--target", str(T), "--live"])
print("exit", rc, "| OUTSIDE now holds:", [str(p.relative_to(O)) for p in O.rglob("*")])
