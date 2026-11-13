#!/usr/bin/env python3
"""Build docs/manifest.json from the files in docs/ and tools/catalog.csv.

Usage:  python3 tools/generate_manifest.py [--docs docs] [--catalog tools/catalog.csv]

catalog.csv is the hand-edited source of truth (one row per file):
    file, title, rp, types, topics
Multiple values in a cell are separated by ";"  e.g.  RP3; RP4
Leave `title` blank to use the title derived from the filename.
New files in docs/ are appended to catalog.csv with best-guess values so you
only need to review them. Rows for deleted files are kept but ignored (warned).
"""
import argparse, csv, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import RPS, TYPES, TOPICS, SITE_TITLE

SITE_FILES = {"index.html", "app.js", "style.css", "manifest.json", ".DS_Store"}
SKIP_DIRS = {"thumbs"}
COLS = ["file", "title", "rp", "types", "topics"]

ID_RE = re.compile(r"^IndigoCarbon_US-1_(\d{4})_(\d{4}[a-z]?)", re.I)


def split(cell):
    return [x.strip() for x in (cell or "").split(";") if x.strip()]


def derive_title_id(name):
    stem = Path(name).stem
    m = ID_RE.match(stem)
    doc_id = ""
    if m:
        doc_id = f"{m.group(1)}-{m.group(2)}"
        rest = stem[m.end():]
        # drop version/FINAL/DRAFT tokens before the title separator
        rest = re.sub(r"^_?v?[\d.]*_?(FINAL|DRAFT)?\s*[-–]?\s*", "", rest, flags=re.I)
        rest = re.sub(r"^v-\s*", "", rest)
        title = rest.strip(" -–_")
        draft = "DRAFT" in stem.upper()
        title = re.sub(r"\s+", " ", title)
        if draft:
            title += " (draft)"
        return title or stem, doc_id
    title = stem.replace("_", " ")
    return re.sub(r"\s+", " ", title).strip(), doc_id


# --- best-guess pre-fill for brand-new catalog rows ---------------------------------
def guess(name):
    n = name.replace("_", " ")
    rp = []
    m = re.search(r"\bRP\s?(\d)\b", n, re.I)
    if m and f"RP{m.group(1)}" in RPS:
        rp = [f"RP{m.group(1)}"]
    types = []
    if re.search(r"monitoring plan", n, re.I): types.append("Monitoring Plan")
    if re.search(r"monitoring report", n, re.I): types.append("Monitoring Report")
    if re.search(r"\bVer\b.*(Opinion|Report)", n, re.I): types.append("Verification Results")
    if re.search(r"validation", n, re.I): types.append("Model Validation Report")
    if not types: types.append("Supporting Document")
    topics = []
    rules = [
        ("Additionality", r"additional|common practice|negative list|tillage rotation|de.?minimis"),
        ("Soil Sampling", r"sampl|bulk density|pH and texture|soil carbon|sanitation|lab|soil.sampling"),
        ("Quantification", r"quantification|equation|post.processing|variance|fossil fuel"),
        ("Modeling", r"model|baseline thread|pre.strata|sensitivity"),
        ("Data Collection", r"data flow|data sources|incomplete|gap.?fill|imput|screen|submittal|input mapping|field data"),
        ("Attestations", r"attestation"),
        ("QA/QC", r"screen|qa|qc|data review|imput|gap.?fill"),
        ("Leakage", r"leakage"),
        ("Guidance", r"clarification|reserve|guidance|procedure|qualifications|SDG"),
    ]
    for t, rx in rules:
        if re.search(rx, n, re.I): topics.append(t)
    return rp, types, topics


def load_catalog(path):
    rows = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("file"): rows[r["file"]] = {c: (r.get(c) or "").strip() for c in COLS}
    return rows


def save_catalog(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for k in sorted(rows, key=str.lower):
            w.writerow(rows[k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="docs")
    ap.add_argument("--catalog", default="tools/catalog.csv")
    a = ap.parse_args()
    docs, cat_path = Path(a.docs), Path(a.catalog)

    files = sorted(p for p in docs.iterdir()
                   if p.is_file() and p.name not in SITE_FILES and not p.name.startswith("."))
    rows = load_catalog(cat_path)
    added = 0
    for p in files:
        if p.name not in rows:
            rp, ty, to = guess(p.name)
            rows[p.name] = {"file": p.name, "title": "", "rp": "; ".join(rp),
                            "types": "; ".join(ty), "topics": "; ".join(to)}
            added += 1
    names = {p.name for p in files}
    for k in rows:
        if k not in names:
            print(f"WARN: catalog row has no file in {docs}: {k}")
    cat_path.parent.mkdir(parents=True, exist_ok=True)
    save_catalog(cat_path, rows)

    out, problems, no_rp = [], 0, 0
    for p in files:
        r = rows[p.name]
        title, doc_id = derive_title_id(p.name)
        if r["title"]: title = r["title"]
        idx = {}
        for key, vocab, col in (("r", RPS, "rp"), ("k", TYPES, "types"), ("c", TOPICS, "topics")):
            vals = split(r[col]); ids = []
            for v in vals:
                if v in vocab: ids.append(vocab.index(v))
                else:
                    print(f"WARN: {p.name}: unknown {col} value {v!r}"); problems += 1
            idx[key] = ids
        if not idx["r"]: no_rp += 1
        rec = {"p": p.name, "t": title, "r": idx["r"], "k": idx["k"], "c": idx["c"],
               "s": p.stat().st_size, "e": p.suffix.lower().lstrip(".")}
        if doc_id: rec["i"] = doc_id
        th = hashlib.sha1(p.name.encode()).hexdigest()[:12] + ".webp"
        if (docs / "thumbs" / th).exists(): rec["m"] = th
        out.append(rec)

    manifest = {"v": 1, "title": SITE_TITLE,
                "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "count": len(out), "bytes": sum(r["s"] for r in out),
                "rps": RPS, "types": TYPES, "topics": TOPICS, "files": out}
    (docs / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    print(f"{len(out)} files, {added} new catalog rows, {problems} bad values, {no_rp} without an RP")


if __name__ == "__main__":
    main()
