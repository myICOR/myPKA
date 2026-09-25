from h import *
print("== P5a member-editable installed manifest: drop 'version' -> downgrade no longer refused")
W = Path("w5"); shutil.rmtree(W, ignore_errors=True); T = W/"mypka"; T.mkdir(parents=True)
installed(T, "mypka", "1.4.0", {"AGENTS.md": "a\n"})
R = release(W/"rel", "mypka", "1.0.0", {"AGENTS.md": "old vulnerable\n"}, previous={"AGENTS.md":[sha(b"a\n")]})
run(R, T, live=False)
m = json.loads((T/".mypka/manifest.json").read_text()); m["version"] = "garbage"; (T/".mypka/manifest.json").write_text(json.dumps(m))
run(R, T, live=False)
print("\n== P7 no authenticity: tamper one file in a release, recompute its hash in the release's own manifest -> accepted")
# A fresh target: T above now holds a garbage version, which the updater
# refuses for that reason alone (P5b). P7 needs a readable 1.4.0 install.
T7 = W/"p7"/"mypka"; installed(T7, "mypka", "1.4.0", {"AGENTS.md": "a\n"})
R2 = release(W/"rel2", "mypka", "1.5.0", {"AGENTS.md": "TAMPERED\n"})
run(R2, T7, live=False)
