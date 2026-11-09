#!/usr/bin/env python3
"""Resolve every identifier in refs.bib and print what it resolves to beside what the entry claims.
    cd ~/papers/paper1 && python3 check_refs.py refs.bib
For each entry with a doi field, or an arXiv number in a note, eprint, url or journal field, the script fetches the
record (doi.org with a citation JSON request, export.arxiv.org for arXiv numbers) and prints the entry key, the bib
title, the resolved title and the resolved year, with MISMATCH where the titles differ beyond punctuation. Entries with
no identifier are listed at the end for a check by hand (a web page, a leaderboard, a repository). Needs the network."""
import json, re, sys, time, urllib.request, urllib.parse

path = sys.argv[1] if len(sys.argv) > 1 else "refs.bib"
src = open(path, encoding="utf-8").read()
entries = re.findall(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}", src, re.S)
def field(body, name):
    m = re.search(r"\b" + name + r"\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\")", body, re.I)
    return re.sub(r"^[{\"]|[}\"]$", "", m.group(1)).strip() if m else ""
def norm(t): return re.sub(r"[^a-z0-9]+", " ", re.sub(r"\\.|[{}]", "", t.lower())).strip()
def get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode("utf-8", "replace")
def resolve_doi(doi):
    j = json.loads(get("https://doi.org/" + urllib.parse.quote(doi), {"Accept": "application/vnd.citationstyles.csl+json"}))
    year = (j.get("issued", {}).get("date-parts") or [[None]])[0][0]
    return j.get("title", ""), year
def resolve_arxiv(aid):
    x = get("https://export.arxiv.org/api/query?id_list=" + aid, {"User-Agent": "check_refs"})
    t = re.search(r"<entry>.*?<title>(.*?)</title>", x, re.S); y = re.search(r"<published>(\d{4})", x)
    return (re.sub(r"\s+", " ", t.group(1)).strip() if t else ""), (y.group(1) if y else None)

unresolved = []
for kind, key, body in entries:
    title = field(body, "title"); year = field(body, "year")
    doi = field(body, "doi")
    blob = " ".join(field(body, f) for f in ("note", "eprint", "url", "journal", "howpublished"))
    arx = re.search(r"(?:arXiv:|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5})", blob)
    try:
        if doi: rtitle, ryear = resolve_doi(doi); via = "doi " + doi
        elif arx: rtitle, ryear = resolve_arxiv(arx.group(1)); via = "arXiv " + arx.group(1)
        else: unresolved.append((key, title)); continue
    except Exception as e:
        print(f"{key}: could not resolve ({e})"); continue
    ok = norm(rtitle) == norm(title) or norm(title) in norm(rtitle) or norm(rtitle) in norm(title)
    print(f"{'ok      ' if ok else 'MISMATCH'} {key} [{via}]\n    bib:      {title} ({year})\n    resolved: {rtitle} ({ryear})")
    time.sleep(1.0)
if unresolved:
    print("\nno identifier, check by hand:")
    for key, title in unresolved: print(f"  {key}: {title}")
print(f"\n{len(entries)} entries, {len(entries) - len(unresolved)} resolved by identifier, {len(unresolved)} by hand")
