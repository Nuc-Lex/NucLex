#!/usr/bin/env python3
"""
Check NucLex identifiers.

Reports:
  - highest class identifier in use, and the next free one, for each range:
    Protege (1-19999, scripts/next_id.txt) and import (20000-79999,
    scripts/next_import_id.txt, used by sync_ncit.py and sync_nucleon.py)
  - whether a counter file is behind (would hand out a used identifier)
  - gaps in the numbering (informational only: gaps are permanent, never fill them)
  - malformed IRIs: entities that look like ours but are not NUCLEX_ + 7 digits,
    e.g. classes created while Protege's new-entity settings were wrong
  - collision symptoms: one IRI carrying several labels or several statuses,
    which is what two terms accidentally given the same identifier look like
  - duplicate labels: two classes sharing exactly the same label (a duplicate
    concept, or a collision). Case-sensitive: K1 and k1 are different terms.
  - with --previous: identifiers that vanished since that release (error) and
    labels that changed (warning)

Read-only. Exits with status 1 if any error is found, so it can run in CI.

Usage:
    python scripts/check_ids.py nuclex-source.owl
    python scripts/check_ids.py nuclex.owl --previous releases/1.0.0/nuclex.owl
"""

import argparse, re, sys
from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL, URIRef

BASE = "https://nuclex.com/id/"
CLASS_RE = re.compile(r"^" + re.escape(BASE) + r"NUCLEX_(\d{7})$")
# A property IRI is readable: lowercase letters, digits, underscores.
PROP_RE = re.compile(r"^" + re.escape(BASE) + r"[a-z][a-z0-9_]*$")
# Namespaces that are not ours; anything else declared as a class or property
# is suspicious (Protege's default namespace has bitten us before).
FOREIGN = (
    "http://www.w3.org/", "http://purl.org/dc/", "http://purl.org/dc/terms/",
    "http://purl.obolibrary.org/", "http://xmlns.com/foaf/",
    "http://www.geneontology.org/", "http://www.w3.org/2004/02/skos/",
)
ENTITY_TYPES = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
                OWL.AnnotationProperty, OWL.NamedIndividual)
MAX_LIST = 25
# (name, (low, high), counter file in scripts/) - see EDITORIAL_POLICY.md 3.3
RANGES = [("Protege", (1, 19999), "next_id.txt"),
          ("import", (20000, 79999), "next_import_id.txt")]


def load(path):
    g = rdflib.Graph()
    with open(path, encoding="utf-8") as fh:
        g.parse(fh, format="xml", publicID=Path(path).resolve().as_uri())
    return g


def prop_by_label(g, name):
    """Find an annotation property by rdfs:label (property IRIs have changed)."""
    for p in sorted(g.subjects(RDF.type, OWL.AnnotationProperty)):
        for l in g.objects(p, RDFS.label):
            if str(l).strip().lower() == name:
                return p
    return None


def labels(g, s):
    return sorted({str(l) for l in g.objects(s, RDFS.label)})


def entities(g):
    out = set()
    for t in ENTITY_TYPES:
        out.update(s for s in g.subjects(RDF.type, t) if isinstance(s, URIRef))
    return out


def class_ids(g):
    """{number: iri} for every well-formed NUCLEX class IRI in the file."""
    ids = {}
    for s in g.subjects(RDF.type, OWL.Class):
        m = CLASS_RE.match(str(s))
        if m:
            ids[int(m.group(1))] = s
    return ids


def show(title, items, level):
    print(f"\n[{level}] {title}: {len(items)}")
    for line in items[:MAX_LIST]:
        print("   ", line)
    if len(items) > MAX_LIST:
        print(f"    ... and {len(items) - MAX_LIST} more")


def gap_ranges(nums):
    out, prev = [], None
    for n in nums:
        if prev is not None and n > prev + 1:
            a, b = prev + 1, n - 1
            out.append(f"{a:07d}" if a == b else f"{a:07d}-{b:07d}")
        prev = n
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ontology")
    ap.add_argument("--previous", help="a previous release to compare against")
    args = ap.parse_args()

    g = load(args.ontology)
    errors = warnings = 0

    ids = class_ids(g)
    if not ids:
        sys.exit("No NUCLEX_ class identifiers found - wrong file?")
    nums = sorted(ids)
    print(f"file              : {args.ontology}")
    print(f"NUCLEX classes    : {len(nums)}")

    # Each range has its own counter file (EDITORIAL_POLICY.md 3.3).
    here = Path(__file__).resolve().parent
    gaps = []
    for name, (lo, hi_r), counter in RANGES:
        in_range = [n for n in nums if lo <= n <= hi_r]
        print(f"\n{name} range {lo}-{hi_r}: {len(in_range)} classes")
        if in_range:
            hi = in_range[-1]
            print(f"  highest identifier: NUCLEX_{hi:07d}")
            print(f"  next free         : NUCLEX_{hi + 1:07d}")
            gaps += gap_ranges(in_range)
        nf = here / counter
        if nf.exists():
            txt = nf.read_text(encoding="utf-8").strip()
            m = re.search(r"(\d+)\s*$", txt)
            if not m:
                show(f"{counter} unreadable", [txt], "ERROR"); errors += 1
            elif in_range and int(m.group(1)) <= in_range[-1]:
                show(f"{counter} would reuse an identifier",
                     [f"file says {txt}, but NUCLEX_{in_range[-1]:07d} is already in use"],
                     "ERROR")
                errors += 1
            else:
                print(f"  {counter:<18}: {txt} (ok)")
    outside = [f"NUCLEX_{n:07d}  {labels(g, ids[n])}" for n in nums
               if not any(lo <= n <= hi_r for _, (lo, hi_r), _ in RANGES)]
    if outside:
        show("identifiers outside every assigned range", outside, "WARN")
        warnings += len(outside)

    if gaps:
        show("gaps in numbering (permanent - never fill)", gaps, "info")

    # malformed IRIs
    bad = []
    for s in sorted(entities(g)):
        u = str(s)
        if u.startswith(FOREIGN) or CLASS_RE.match(u):
            continue
        if u.startswith(BASE) and PROP_RE.match(u) and (s, RDF.type, OWL.Class) not in g:
            continue
        lab = labels(g, s)
        bad.append(f"{u}  {lab[0] if lab else '(no label)'}")
    if bad:
        show("malformed or foreign-namespace IRIs", bad, "ERROR"); errors += len(bad)

    # collision symptoms
    multi_label = []
    for n in nums:
        lab = labels(g, ids[n])
        if len(lab) > 1:
            multi_label.append(f"NUCLEX_{n:07d}  {lab}")
    if multi_label:
        show("classes with more than one rdfs:label", multi_label, "ERROR")
        errors += len(multi_label)

    by_label = {}
    for n in nums:
        for l in labels(g, ids[n]):
            by_label.setdefault(" ".join(l.split()), []).append(n)
    dup_label = [f"{k!r}: " + ", ".join(f"NUCLEX_{n:07d}" for n in v)
                 for k, v in sorted(by_label.items()) if len(set(v)) > 1]
    if dup_label:
        show("labels shared by more than one class", dup_label, "ERROR")
        errors += len(dup_label)

    status = prop_by_label(g, "status")
    if status is not None:
        multi_status = []
        for n in nums:
            vals = sorted({str(v) for v in g.objects(ids[n], status)})
            if len(vals) > 1:
                multi_status.append(f"NUCLEX_{n:07d}  {labels(g, ids[n])}  {vals}")
        if multi_status:
            show("classes with more than one status", multi_status, "ERROR")
            errors += len(multi_status)

    # comparison with a previous release
    if args.previous:
        pg = load(args.previous)
        pids = class_ids(pg)
        print(f"\nprevious release  : {args.previous} ({len(pids)} classes)")
        vanished = [f"NUCLEX_{n:07d}  {labels(pg, pids[n])}"
                    for n in sorted(set(pids) - set(ids))]
        if vanished:
            show("identifiers that vanished (deprecate, never delete)", vanished, "ERROR")
            errors += len(vanished)
        changed = []
        for n in sorted(set(pids) & set(ids)):
            old, new = labels(pg, pids[n]), labels(g, ids[n])
            if old != new:
                changed.append(f"NUCLEX_{n:07d}  {old} -> {new}")
        if changed:
            show("labels changed since previous release (check intended)", changed, "WARN")
            warnings += len(changed)
        added = len(set(ids) - set(pids))
        print(f"\nnew identifiers since previous release: {added}")

    print(f"\n{errors} error(s), {warnings} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
