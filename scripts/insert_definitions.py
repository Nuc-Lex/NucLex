#!/usr/bin/env python3
"""
Insert reviewed definitions and synonyms into NucLex.

Reads the edited TSV, matches rows to classes by IRI, and adds
skos:definition and skos:altLabel. Never overwrites an existing
definition and never removes anything.

Usage:
    python scripts/insert_definitions.py nuclex-source.owl contributions/incoming/defs.tsv
    python scripts/insert_definitions.py nuclex-source.owl contributions/incoming/defs.tsv --dry-run
    python scripts/insert_definitions.py nuclex-source.owl contributions/incoming/defs.tsv --out nuclex-source-new.owl
    python scripts/insert_definitions.py nuclex-source.owl contributions/incoming/defs.tsv --force   # replace existing defs

Writes to a NEW file; the input ontology is never modified in place.
"""

import sys, csv, argparse
import rdflib
from rdflib import RDF, RDFS, OWL, URIRef, Literal

SKOS = "http://www.w3.org/2004/02/skos/core#"
DEFN = URIRef(SKOS + "definition")
ALT  = URIRef(SKOS + "altLabel")

DEF_COL  = "proposed_definition"
SYN_COL  = "proposed_new_synonyms"
IRI_COL  = "iri"
LAB_COL  = "label"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ontology")
    ap.add_argument("table")
    ap.add_argument("--out", default=None,
                    help="output file (default: <ontology stem>-defs.owl)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="replace an existing definition instead of skipping it")
    ap.add_argument("--lang", default=None,
                    help="language tag to attach, e.g. en (default: none)")
    args = ap.parse_args()

    out = args.out or args.ontology.rsplit(".", 1)[0] + "-defs.owl"

    g = rdflib.Graph()
    g.parse(args.ontology)
    classes = {str(c) for c in g.subjects(RDF.type, OWL.Class)}
    print(f"ontology: {len(g)} triples, {len(classes)} classes")

    def lit(t):
        return Literal(t, lang=args.lang) if args.lang else Literal(t)

    # ---- read the table -------------------------------------------------
    with open(args.table, encoding="utf-8-sig", newline="") as fh:
        sample = fh.readline()
        fh.seek(0)
        if "\t" not in sample:
            sys.exit("ERROR: no tab found in the header row. Save the file as "
                     "tab-separated, not comma-separated.")
        rows = list(csv.DictReader(fh, delimiter="\t"))

    for col in (IRI_COL, LAB_COL, DEF_COL):
        if col not in rows[0]:
            sys.exit(f"ERROR: column {col!r} not found. Columns present: "
                     f"{list(rows[0])}")
    print(f"table: {len(rows)} rows")

    # ---- apply ----------------------------------------------------------
    added_def = replaced_def = skipped_had_def = blank_def = 0
    added_syn = dup_syn = same_as_label = 0
    not_found, label_mismatch, style = [], [], []

    for r in rows:
        iri = (r.get(IRI_COL) or "").strip()
        lab = (r.get(LAB_COL) or "").strip()
        if not iri:
            continue
        if iri not in classes:
            not_found.append((iri, lab))
            continue

        subj = URIRef(iri)
        actual = [str(x) for x in g.objects(subj, RDFS.label)]
        if lab and actual and lab not in actual:
            label_mismatch.append((iri, lab, actual[0]))
            continue                      # stale row: do not touch it

        # -- definition
        d = (r.get(DEF_COL) or "").strip()
        if not d:
            blank_def += 1
        else:
            if not d.endswith("."):
                style.append((lab, "no final period"))
            if d[:1].islower():
                style.append((lab, "starts lowercase"))
            existing = list(g.objects(subj, DEFN))
            if existing and not args.force:
                skipped_had_def += 1
            else:
                for e in existing:
                    g.remove((subj, DEFN, e))
                    replaced_def += 1
                g.add((subj, DEFN, lit(d)))
                if not existing:
                    added_def += 1

        # -- synonyms (add only; never replace)
        have = {str(x).strip().lower() for x in g.objects(subj, ALT)}
        labels_lower = {a.strip().lower() for a in actual}
        for s in (r.get(SYN_COL) or "").split(";"):
            s = s.strip()
            if not s:
                continue
            if s.lower() in labels_lower:
                same_as_label += 1
            elif s.lower() in have:
                dup_syn += 1
            else:
                g.add((subj, ALT, lit(s)))
                have.add(s.lower())
                added_syn += 1

    # ---- report ---------------------------------------------------------
    print("\n--- definitions ---")
    print(f"  added                : {added_def}")
    print(f"  replaced (--force)   : {replaced_def}")
    print(f"  skipped, already had : {skipped_had_def}")
    print(f"  blank in table       : {blank_def}")
    print("--- synonyms ---")
    print(f"  added                : {added_syn}")
    print(f"  skipped, duplicate   : {dup_syn}")
    print(f"  skipped, = the label : {same_as_label}")

    if not_found:
        print(f"\n!! {len(not_found)} IRIs in the table are not classes in the "
              f"ontology (nothing written for these):")
        for i, l in not_found[:15]:
            print(f"     {i}  {l}")
    if label_mismatch:
        print(f"\n!! {len(label_mismatch)} rows SKIPPED because the label does not "
              f"match the ontology (stale row?):")
        for i, t, a in label_mismatch[:15]:
            print(f"     {i}\n        table: {t!r}\n        owl  : {a!r}")
    if style:
        print(f"\n   {len(style)} style notes:")
        for l, m in style[:15]:
            print(f"     {l}: {m}")

    if args.dry_run:
        print("\nDRY RUN - nothing written.")
        return
    if not_found or label_mismatch:
        print("\nWriting anyway; the rows listed above were skipped.")

    g.serialize(destination=out, format="pretty-xml")
    print(f"\nwrote {len(g)} triples -> {out}")


if __name__ == "__main__":
    main()