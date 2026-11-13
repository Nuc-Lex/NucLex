#!/usr/bin/env python3
"""
Bring the radionuclide branch up to date with NUCLEON.

NUCLEON (https://github.com/RSNA/NUCLEON) is RSNA's Nuclide and Element
Ontology. NucLex takes only the nuclide's name and its NUCLEON IRI, recorded in
nucleon_id. No physics properties are inherited (NUCLEON is CC BY-NC-ND).

  1. Every existing class under 'radionuclide' is matched to its NUCLEON
     nuclide (by nucleon_id, else by its label, e.g. 'Lutetium-177') and given
     a nucleon_id if it lacks one. Nothing else about it changes.
  2. Selected unstable nuclides not yet in NucLex are added under
     'radionuclide', with:
        label       'Lutetium-177'   (from NUCLEON's English name)
        synonym     'Lu-177'         (NUCLEON's label)
        definition  generated from mass number, atomic number and half-life
        nucleon_id  the NUCLEON IRI
     Default selection: radionuclides with a DICOM code (DICOM CID 18 and
     CID 4020), i.e. the ones used clinically. --select all-unstable takes all.

Nuclides listed in scripts/nucleon_skip.txt (e.g. Lu-177m) are never added.

Writes a NEW ontology file and a report TSV. Never modifies the input.

Usage:
    python scripts/sync_nucleon.py nuclex-source.owl --dry-run
    python scripts/sync_nucleon.py nuclex-source.owl --out nuclex-source-nucleon.owl
    python scripts/sync_nucleon.py nuclex-source.owl --nucleon path/to/NUCLEON.ttl ...
"""

import argparse, re, sys
import rdflib
from rdflib import RDF, RDFS, Literal, Namespace, URIRef
import nxlib
from nxlib import SKOS

NUCLEON_URL = "https://raw.githubusercontent.com/RSNA/NUCLEON/main/NUCLEON.ttl"
N = Namespace("https://rsna.org/radlex/nucleon#")

UNITS = {"as": "attoseconds", "ps": "picoseconds", "ns": "nanoseconds",
         "µs": "microseconds", "us": "microseconds", "ms": "milliseconds",
         "s": "seconds", "m": "minutes", "h": "hours", "d": "days", "a": "years"}
SECONDS = [(365.25 * 86400, "years"), (86400, "days"), (3600, "hours"),
           (60, "minutes"), (1, "seconds"), (1e-3, "milliseconds"),
           (1e-6, "microseconds"), (1e-9, "nanoseconds")]


def one(g, s, p):
    v = sorted(g.objects(s, p))
    return v[0] if v else None


def half_life(n, s):
    """'6.6443 days' from NUCLEON's source value and unit, else from seconds."""
    val, unit = one(n, s, N.halfLifeValue), one(n, s, N.halfLifeUnit)
    if val is not None and unit is not None and str(unit) in UNITS:
        num, word = float(val), UNITS[str(unit)]
        text = f"{val}"
    else:
        secs = one(n, s, N.halfLife)
        if secs is None:
            return None
        secs = float(secs)
        factor, word = next(((f, w) for f, w in SECONDS if secs >= f), SECONDS[-1])
        num = secs / factor
        text = f"{num:.4g}"
    if num == 1:
        word = word[:-1]
    return f"{text} {word}"


def definition(n, s):
    a, z = one(n, s, N.massNumber), one(n, s, N.atomicNumber)
    isomer = re.search(r"\d+m\d*$", local(s)) is not None
    head = ("A metastable excited state of a nuclide" if isomer
            else "An unstable nuclide")
    hl = half_life(n, s)
    tail = f", with a half-life of {hl}." if hl else "."
    return f"{head} with {a} nucleons and {z} protons{tail}"


def local(s):
    return str(s).rsplit("#", 1)[-1]


def english_name(n, s):
    """'lutetium-177' -> 'Lutetium-177'."""
    for l in sorted(n.objects(s, SKOS.altLabel)):
        if getattr(l, "language", None) == "en" and re.match(r"^[a-z]+-\d+", str(l)):
            t = str(l)
            return t[0].upper() + t[1:]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ontology")
    ap.add_argument("--nucleon", default=NUCLEON_URL, help="NUCLEON.ttl path or URL")
    ap.add_argument("--out", default="nuclex-source-nucleon.owl")
    ap.add_argument("--report", default="nucleon_sync_report.tsv")
    ap.add_argument("--select", choices=("dicom", "all-unstable"), default="dicom")
    ap.add_argument("--status", default="approved", help="status for new terms")
    ap.add_argument("--skip-file", default=str(nxlib.SCRIPTS / "nucleon_skip.txt"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = nxlib.load(args.ontology)
    status_p = nxlib.prop_by_label(g, "status")
    nucleon_p, declared = nxlib.ensure_prop(
        g, "nucleon_id", "nucleon id",
        "A code identifying a corresponding nuclide in NUCLEON, the Nuclide and "
        "Element Ontology.")
    if declared:
        print("declared new annotation property nx:nucleon_id")

    print(f"loading NUCLEON from {args.nucleon} ...")
    n = rdflib.Graph()
    n.parse(args.nucleon, format="turtle")
    version = next((str(v) for o in n.subjects(RDF.type, rdflib.OWL.Ontology)
                    for v in n.objects(o, rdflib.OWL.versionInfo)), "?")
    nuclides = set(n.subjects(RDF.type, N.Nuclide))
    print(f"NUCLEON {version}: {len(nuclides)} nuclides")

    by_name = {}
    for s in nuclides:
        e = english_name(n, s)
        if e:
            by_name[e.lower()] = s

    root = nxlib.class_by_label(g, "radionuclide")
    existing = nxlib.descendants(g, root) - {root}
    report, matched = [], set()

    # ---- 1. map existing radionuclides ------------------------------------
    for c in sorted(existing, key=lambda c: nxlib.label(g, c)):
        lab = nxlib.label(g, c)
        have = [URIRef(str(v)) for v in g.objects(c, nucleon_p)]
        if have:
            matched.update(have)
            continue
        s = by_name.get(lab.lower())
        if s is None:
            report.append(("not matched", str(c), "", lab, "",
                           "no NUCLEON nuclide with this name; map by hand if it is a nuclide"))
            continue
        g.add((c, nucleon_p, Literal(str(s))))
        matched.add(s)
        report.append(("mapped", str(c), str(s), lab, local(s), "nucleon_id added"))

    # ---- 2. add selected nuclides -----------------------------------------
    unstable = {s for s in nuclides if (s, N.isStable, Literal(False)) in n}
    if args.select == "dicom":
        selected = {s for s in unstable if (s, N.dicomCode, None) in n}
    else:
        selected = unstable
    skip = nxlib.read_skip_file(args.skip_file)
    labels_in_use = {nxlib.label(g, c) for c in g.subjects(RDF.type, rdflib.OWL.Class)}

    minter = nxlib.Minter(g)
    for s in sorted(selected - matched, key=lambda s: (int(one(n, s, N.atomicNumber)), local(s))):
        if local(s) in skip:
            report.append(("skipped", "", str(s), "", local(s), "listed in skip file"))
            continue
        lab = english_name(n, s)
        if not lab:
            report.append(("not added", "", str(s), "", local(s), "no English name in NUCLEON"))
            continue
        if lab in labels_in_use:
            report.append(("not added", "", str(s), lab, local(s),
                           "a NucLex class already has this label outside 'radionuclide'"))
            continue
        extra = [(nucleon_p, str(s)), (SKOS.altLabel, local(s)),
                 (SKOS.definition, definition(n, s))]
        iri = nxlib.add_class(g, minter, lab, [root], status_p, args.status, extra)
        report.append(("added", str(iri), str(s), lab, local(s), definition(n, s)))

    # ---- output -----------------------------------------------------------
    counts = {}
    for r in report:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print(f"\nselection: {args.select} -> {len(selected)} nuclides, "
          f"{len(selected & matched)} already in NucLex")
    print("result")
    for k in ("mapped", "added", "not matched", "not added", "skipped"):
        print(f"  {k:<12} {counts.get(k, 0)}")
    for r in report:
        if r[0] in ("not matched", "not added"):
            print(f"    {r[0]:<12} {r[3] or r[4]}   [{r[5]}]")

    nxlib.write_report(args.report, ("action", "nuclex_iri", "nucleon_iri", "nuclex_label",
                                     "nucleon_label", "note"), report)
    print(f"\nreport -> {args.report}")
    if args.dry_run:
        print("DRY RUN - ontology not written.")
        return
    nxlib.save(g, args.out)
    minter.commit()
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
