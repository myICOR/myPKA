# P1: mode A, a myPKA release overwrites ICOR's file and ICOR's manifest through a case-only variant of the path
from h import *
W = Path("w1"); shutil.rmtree(W, ignore_errors=True)
T = W / "vault"; T.mkdir(parents=True)
installed(T, "icor", "2.0.0", {"README.md": "ICOR readme\n", "04 Inner World/Journal/j.md": "journal\n"})
installed(T, "mypka", "1.0.0", {"AGENTS.md": "team\n"})
icor_man = (T/".icor-for-life/manifest.json").read_bytes()
evil = "OVERWRITTEN BY A MYPKA RELEASE\n"
R = release(W/"rel", "mypka", "1.1.0", {"AGENTS.md": "team v2\n", "readme.md": evil, ".ICOR-for-life/manifest.json": '{"name":"icor","version":"0.0.1","files":{}}'},
            previous={"readme.md": [sha(b"ICOR readme\n")], ".ICOR-for-life/manifest.json": [sha(icor_man)]})
run(R, T)
print("README.md now:", (T/"README.md").read_text().strip())
print("ICOR manifest now:", (T/".icor-for-life/manifest.json").read_text()[:80])
print("names on disk:", sorted(os.listdir(T)))
