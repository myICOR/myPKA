import importlib.util, fix
from h import *
spec = importlib.util.spec_from_file_location("up", UP); up = importlib.util.module_from_spec(spec); spec.loader.exec_module(up)
orig_main = up.main
# swap in the proposed writer: same call sites, (src, root, rel)
def patched_main(argv):
    def wa(src, dest):
        # recover (root, rel) from the call site: dest = target / rel
        root = Path(TGT); fix.write_atomic(src, root, str(Path(dest).relative_to(root)))
    up.write_atomic = wa
    return orig_main(argv)
# P4 again
W = Path("v4"); shutil.rmtree(W, ignore_errors=True); T = W/"mypka"; T.mkdir(parents=True); O = W/"OUTSIDE"; O.mkdir(); TGT = str(T.resolve())
installed(T, "mypka", "1.0.0", {"AGENTS.md": "a\n", "06 AI Team/Scripts/x.py": "old\n"})
R = release(W/"rel", "mypka", "1.1.0", {"AGENTS.md": "b\n", "06 AI Team/Scripts/x.py": "new\n"})
rp = up.plan
def racing(args):
    out = rp(args); shutil.rmtree(T/"06 AI Team"); os.symlink(O.resolve(), T/"06 AI Team"); return out
up.plan = racing
try: patched_main(["x","--release",str(R),"--target",str(T),"--live"])
except OSError as e: print("P4 with fix: refused by the OS:", type(e).__name__, e.strerror)
print("P4 OUTSIDE:", [str(p.relative_to(O)) for p in O.rglob("*")])
up.plan = rp
# P6 again
W = Path("v6"); shutil.rmtree(W, ignore_errors=True); T = W/"mypka"; T.mkdir(parents=True); O = W/"OUTSIDE"; O.mkdir(); TGT = str(T.resolve())
(T/"AGENTS.md").write_text("a\n"); os.symlink(O.resolve(), T/".mypka")
R = mk(W/"rel", {"AGENTS.md": "b\n"}); (R/".mypka").mkdir(); (R/".mypka/manifest.json").write_text(json.dumps({"version":"1.1.0","files":{"AGENTS.md": sha(b"b\n")}}))
try: patched_main(["x","--release",str(R),"--target",str(T),"--live"])
except OSError as e: print("P6 with fix: refused by the OS:", type(e).__name__, e.strerror)
print("P6 OUTSIDE:", os.listdir(O))
# clean control: a normal update still applies
W = Path("v0"); shutil.rmtree(W, ignore_errors=True); T = W/"mypka"; T.mkdir(parents=True); TGT = str(T.resolve())
installed(T, "mypka", "1.0.0", {"AGENTS.md": "a\n"})
R = release(W/"rel", "mypka", "1.1.0", {"AGENTS.md": "b\n", "new/dir/f.md": "n\n"})
print("control exit", patched_main(["x","--release",str(R),"--target",str(T),"--live"]), (T/"AGENTS.md").read_text().strip(), (T/"new/dir/f.md").exists())
