"""Refetch the RFC corpus and rebuild the store. The exam itself is
committed (authored for this demo, machine-verified against these texts);
only the corpus regenerates."""
import json, re, sqlite3, subprocess, time
from pathlib import Path

CORE = [791, 793, 821, 822, 959, 1034, 1035, 1945, 2045, 2046, 2181, 2616,
        2818, 3986, 4271, 4291, 5321, 5322, 5646, 6265, 6455, 6749, 6750,
        6811, 7230, 7231, 7232, 7233, 7234, 7235, 7413, 7519, 7540, 7541,
        7617, 8017, 8032, 8200, 8259, 8446, 8484, 8555, 8615, 8949, 9000,
        9001, 9110, 9111, 9112, 9113, 9114, 9147, 9162, 9293, 9309, 9457,
        9562, 9580]
Path("corpus").mkdir(exist_ok=True)
for n in dict.fromkeys(CORE):
    out = Path(f"corpus/rfc{n}.txt")
    if out.exists():
        continue
    r = subprocess.run(["curl", "-sS", "--max-time", "30",
                        f"https://www.rfc-editor.org/rfc/rfc{n}.txt"],
                       capture_output=True, text=True)
    if r.returncode == 0 and len(r.stdout) > 5000:
        out.write_text(r.stdout)
    time.sleep(0.3)

# Verify the committed exam against the fetched texts -- the same bar
# authoring used: an answer whose key claim cannot be found in its source
# is named, loudly. (authored-verified.json carries the strict patterns.)
missing_docs, mismatches = [], []
for p_ in json.load(open("authored-verified.json")):
    path = Path(f"corpus/{p_['rfc']}.txt")
    if not path.exists():
        missing_docs.append(p_["rfc"])
        continue
    text = path.read_text(errors="replace").lower()
    key = p_["a"].split("\u2014")[0].split(",")[0].strip().lower()[:24]
    if key and key not in text:
        mismatches.append((p_["rfc"], p_["q"][:50]))
if missing_docs:
    print(f"WARNING: {len(missing_docs)} source RFC(s) failed to fetch: {sorted(set(missing_docs))}")
for rfc, q in mismatches:
    print(f"WARNING: key claim not found in {rfc}: {q}")
print(f"exam verification: {len(mismatches)} mismatch(es), {len(missing_docs)} missing doc(s)")

con = sqlite3.connect("standards.db")
con.execute("CREATE TABLE IF NOT EXISTS standards (id TEXT PRIMARY KEY, body TEXT)")
for f in sorted(Path("corpus").glob("*.txt")):
    con.execute("INSERT OR REPLACE INTO standards VALUES (?,?)",
                (f.stem, f.read_text(errors="replace")))
con.commit()
# The deliverable reads project/data/corpus -- populate it too.
proj = Path("project/data/corpus")
proj.mkdir(parents=True, exist_ok=True)
for f in Path("corpus").glob("*.txt"):
    (proj / f.name).write_text(f.read_text(errors="replace"))
print("corpus", len(list(Path('corpus').glob('*.txt'))), "docs; store rebuilt;",
      "project/data/corpus populated")
