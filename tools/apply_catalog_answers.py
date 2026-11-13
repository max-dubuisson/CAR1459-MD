#!/usr/bin/env python3
"""Merge catalog_answers.json (from catalog_form.html) into tools/catalog.csv.
Usage: python3 tools/apply_catalog_answers.py path/to/catalog_answers.json   (from repo root)
"""
import csv, json, sys
ans = json.load(open(sys.argv[1], encoding="utf-8"))
rows = list(csv.DictReader(open("tools/catalog.csv", newline="", encoding="utf-8-sig")))
n = 0
for r in rows:
    a = ans.get(r["file"])
    if not a: continue
    for col, key in (("rp", "rp"), ("types", "types"), ("topics", "topics")):
        new = "; ".join(a[key])
        if new != r[col]: r[col] = new; n += 1
with open("tools/catalog.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"{n} cells updated")
