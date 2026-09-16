"""Add harness_sha / machine / red_agent to trace headers in oracle.py and capture.py."""
import re, sys, shutil

BLOCK = '''
# --- provenance (added 2026-09-15) ---
import os as _os, platform as _platform, subprocess as _subprocess

def _harness_sha():
    sha = _os.environ.get("HARNESS_SHA")
    if sha:
        return sha
    try:
        here = _os.path.dirname(_os.path.abspath(__file__))
        return _subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=here,
                                        stderr=_subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"

HARNESS_SHA = _harness_sha()
MACHINE = _platform.node()
RED_AGENT_NAME = "FiniteStateRedAgent"   # overwritten where --red is resolved
# --- end provenance ---
'''

KEYS = '"record": "header", "harness_sha": HARNESS_SHA, "machine": MACHINE, "red_agent": RED_AGENT_NAME,'

def patch(path):
    src = open(path).read()
    if "HARNESS_SHA" in src:
        print(f"{path}: already patched"); return
    shutil.copy(path, path + ".bak")
    # insert block after the last top-level import line
    lines = src.splitlines(keepends=True)
    last = max(i for i, l in enumerate(lines) if re.match(r"^(import|from)\s", l))
    lines.insert(last + 1, BLOCK)
    src = "".join(lines)
    # add keys to the header dict
    n = src.count('"record": "header",')
    if n == 0:
        print(f"{path}: header literal not found; add keys by hand"); 
    else:
        src = src.replace('"record": "header",', KEYS)
        print(f"{path}: header patched ({n} site{'s' if n>1 else ''})")
    open(path, "w").write(src)
    print(f"{path}: provenance block inserted after line {last+1}; backup at {path}.bak")

for p in sys.argv[1:]:
    patch(p)
