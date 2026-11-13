#!/usr/bin/env python3
"""
Build a release copy of NucLex from the working file.

  - strips curation metadata (approver_id, assigned_to, ...)
  - optionally keeps only approved terms, reparenting the children of any
    class it removes so nothing is orphaned

The working file is never modified.

Usage:
    python scripts/build_release.py nuclex-source.owl --out releases/1.0.0/nuclex.owl
    python scripts/build_release.py nuclex-source.owl --only-approved --dry-run
    python scripts/build_release.py nuclex-source.owl --only-approved --keep-status \
           --out releases/1.0.0/nuclex.owl
"""

import argparse, sys
from collections import defaultdict
import rdflib
from rdflib import RDF, RDFS, OWL, URIRef

DEFAULT_STRIP = "approver_id,assigned_to"


def norm(name):
    """'approver_id', 'Approver ID' and 'approver id' all compare equal."""
    return " ".join(str(name).replace("_", " ").lower().split())


def props_by_label(g, names):
    """Find annotation properties by their rdfs:label.

    Returns {name as passed, lowercased: property}. Underscores and spaces are
    treated alike, so --strip approver_id finds the property labelled
    'approver id'.
    """
    want = {norm(n): n.strip().lower() for n in names if n.strip()}
    found = {}
    for p in g.subjects(RDF.type, OWL.AnnotationProperty):
        for l in g.objects(p, RDFS.label):
            key = want.get(norm(l))
            if key is not None:
                found[key] = p
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default="nuclex-release.owl")
    ap.add_argument("--strip", default=DEFAULT_STRIP,
                    help=f"annotation properties to remove (default: {DEFAULT_STRIP})")
    ap.add_argument("--only-approved", action="store_true",
                    help="remove classes whose status is not 'approved'")
    ap.add_argument("--status-value", default="approved")
    ap.add_argument("--keep-status", action="store_true",
                    help="keep the status annotation in the release")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = rdflib.Graph(); g.parse(args.input)
    classes = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    label = {}
    for c in classes:
        ls = list(g.objects(c, RDFS.label))
        label[c] = str(ls[0]) if ls else "(no label)"
    print(f"input: {len(g)} triples, {len(classes)} classes")

    # ---- 1. find the properties we care about ---------------------------
    strip_names = [s for s in args.strip.split(",") if s.strip()]
    strip_props = props_by_label(g, strip_names)
    for n in strip_names:
        if n.strip().lower() not in strip_props:
            print(f"  note: no annotation property labelled {n.strip()!r}")

    status_prop = props_by_label(g, ["status"]).get("status")
    if args.only_approved and status_prop is None:
        sys.exit("ERROR: --only-approved needs an annotation property "
                 "labelled 'status', and none was found.")

    # ---- 2. decide what to remove ---------------------------------------
    remove = set()
    if args.only_approved:
        target = args.status_value.strip().lower()
        for c in classes:
            vals = {str(o).strip().lower() for o in g.objects(c, status_prop)}
            if target not in vals:
                remove.add(c)

        print(f"\nclasses not '{target}': {len(remove)}")
        bylab = sorted(remove, key=lambda c: label[c])
        for c in bylab[:15]:
            print(f"   {label[c]}")
        if len(bylab) > 15:
            print(f"   ... and {len(bylab)-15} more")

        # who would be orphaned?
        kids = defaultdict(set)
        for s, o in g.subject_objects(RDFS.subClassOf):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                kids[o].add(s)
        rescued = [(p, [k for k in kids[p] if k not in remove])
                   for p in remove if any(k not in remove for k in kids[p])]
        n_kids = sum(len(k) for _, k in rescued)
        if rescued:
            print(f"\n{n_kids} kept classes sit under a removed parent and will "
                  f"be reparented:")
            for p, ks in sorted(rescued, key=lambda t: -len(t[1]))[:10]:
                print(f"   {len(ks):>4} children of {label[p]!r}")

    # ---- 3. apply --------------------------------------------------------
    n_strip = 0
    for p in strip_props.values():
        for t in list(g.triples((None, p, None))):
            g.remove(t); n_strip += 1
        for t in list(g.triples((p, None, None))):
            g.remove(t)
    if args.only_approved and not args.keep_status and status_prop is not None:
        for t in list(g.triples((None, status_prop, None))):
            g.remove(t); n_strip += 1
        for t in list(g.triples((status_prop, None, None))):
            g.remove(t)

    n_reparented = 0
    if args.only_approved:
        # bridge: a kept class under a removed parent inherits that parent's parents
        parents = defaultdict(set)
        for s, o in g.subject_objects(RDFS.subClassOf):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                parents[s].add(o)

        def surviving_ancestors(c, seen=None):
            seen = seen or set()
            out = set()
            for p in parents[c]:
                if p in seen:
                    continue
                seen.add(p)
                if p in remove:
                    out |= surviving_ancestors(p, seen)
                else:
                    out.add(p)
            return out

        for c in classes - remove:
            for p in list(parents[c]):
                if p in remove:
                    g.remove((c, RDFS.subClassOf, p))
                    for anc in surviving_ancestors(p):
                        g.add((c, RDFS.subClassOf, anc))
                        n_reparented += 1

        for c in remove:
            for t in list(g.triples((c, None, None))):
                g.remove(t)
            for t in list(g.triples((None, None, c))):
                g.remove(t)

    left = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    print(f"\n--- result ---")
    print(f"  curation annotations removed : {n_strip}")
    print(f"  classes removed              : {len(classes) - len(left)}")
    print(f"  subClassOf links rewired     : {n_reparented}")
    print(f"  classes remaining            : {len(left)}")

    # anything left dangling?
    orphans = [c for c in left
               if not list(g.objects(c, RDFS.subClassOf))]
    print(f"  classes with no parent       : {len(orphans)}")
    for c in sorted(orphans, key=lambda x: label[x])[:12]:
        print(f"      {label[c]}")

    if args.dry_run:
        print("\nDRY RUN - nothing written.")
        return
    g.serialize(destination=args.out, format="pretty-xml")
    print(f"\nwrote {len(g)} triples -> {args.out}")


if __name__ == "__main__":
    main()
