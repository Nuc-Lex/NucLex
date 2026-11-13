#!/usr/bin/env python3
"""
NucLex QC checks. One run does all of them.

  1. approved concepts with no definition          -> *_missing_definition.tsv
  2. approved concepts with no synonym (altLabel)  -> *_missing_synonym.tsv
  3. approved concepts whose parent is not approved -> *_unapproved_parent.tsv
     (must be 0 before a release is built)
  4. classes with no status                        -> *_no_status.tsv
  5. classes with a status outside --allowed       -> *_invalid_status.tsv
  6. classes with more than one status             -> *_multiple_status.tsv
  Files 4-6 are only written when there is something to report.

Checks 1 and 2 skip the DEFAULT_EXCLUDED_BRANCHES below (inherited from
NCI Thesaurus without definitions). Checks 3-6 cover every class.

Files 1 and 2 are worksheets: fill in the proposed_* columns and pass the
file to insert_definitions.py.

Annotation properties are found by their rdfs:label, not by a hard-coded IRI.

Usage:
    python scripts/find_problematic_terms.py nuclex-source.owl
    python scripts/find_problematic_terms.py nuclex-source.owl --check-all-branches
    python scripts/find_problematic_terms.py nuclex-source.owl --exclude-branch "some label"
"""

import sys, argparse
from collections import defaultdict, Counter
import rdflib
from rdflib import RDF, RDFS, OWL, URIRef

SKOS = "http://www.w3.org/2004/02/skos/core#"

# candidate IRIs, tried in order, before falling back to a label lookup
DEF_IRIS = [SKOS + "definition",
            "http://purl.obolibrary.org/obo/IAO_0000115",
            "http://nuclex.org/NID/definition"]
SYN_IRIS = [SKOS + "altLabel",
            "http://www.geneontology.org/formats/oboInOwl#hasExactSynonym",
            "http://www.geneontology.org/formats/oboInOwl#hasRelatedSynonym",
            "http://nuclex.org/NID/synonym"]

# Exempt from the definition and synonym checks: imported without definitions.
DEFAULT_EXCLUDED_BRANCHES = ["radiopharmaceutical compound"]


def find_props(g, candidates, label_names):
    """Return every annotation property matching a candidate IRI or a label."""
    found = []
    for iri in candidates:
        p = URIRef(iri)
        if (p, RDF.type, OWL.AnnotationProperty) in g or list(g.subject_objects(p)):
            found.append(p)
    for p in g.subjects(RDF.type, OWL.AnnotationProperty):
        for l in g.objects(p, RDFS.label):
            if str(l).strip().lower() in label_names and p not in found:
                found.append(p)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--allowed", default="draft,needs approval,approved",
                    help="comma-separated list of permitted status values")
    ap.add_argument("--status", default="approved",
                    help="status value counted as approved (case-insensitive)")
    ap.add_argument("--out-prefix", default="nuclex_qc")
    ap.add_argument("--exclude-branch", action="append", default=[], metavar="LABEL_OR_IRI",
                    help="exempt this class and all its descendants from the "
                         "definition and synonym checks. Repeatable. Added to "
                         f"the defaults: {DEFAULT_EXCLUDED_BRANCHES}")
    ap.add_argument("--check-all-branches", action="store_true",
                    help="do not apply the default branch exclusions")
    args = ap.parse_args()
    if not args.check_all_branches:
        args.exclude_branch = DEFAULT_EXCLUDED_BRANCHES + args.exclude_branch
    TARGET = args.status.strip().lower()

    g = rdflib.Graph()
    g.parse(args.input)

    classes = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    label = {}
    for c in classes:
        ls = list(g.objects(c, RDFS.label))
        label[c] = str(ls[0]) if ls else "(no label)"

    status_props = find_props(g, [], {"status"})
    def_props    = find_props(g, DEF_IRIS, {"definition", "textual definition"})
    syn_props    = find_props(g, SYN_IRIS, {"synonym", "altlabel", "alternative label"})

    print("resolved properties")
    for name, props in (("status", status_props), ("definition", def_props),
                        ("synonym", syn_props)):
        print(f"   {name:<11}", [str(p) for p in props] or "** NONE FOUND **")
    if not status_props:
        sys.exit("\nERROR: no annotation property labelled 'status'. "
                 "Pass the right file, or add the label.")

    def values(c, props):
        return [str(o) for p in props for o in g.objects(c, p)]

    ALLOWED = {a.strip().lower() for a in args.allowed.split(",") if a.strip()}
    status, multi_status, no_status, bad_status = {}, [], [], []
    for c in classes:
        v = sorted({x.strip().lower() for x in values(c, status_props)})
        if len(v) > 1:
            multi_status.append((c, v))
        if not v:
            no_status.append(c)
        for one in v:
            if one not in ALLOWED:
                bad_status.append((c, one))
        status[c] = v[0] if v else None      # deterministic: alphabetically first

    parents = defaultdict(set)
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            parents[s].add(o)

    approved = {c for c in classes if status[c] == TARGET}

    # ---- branches exempt from the definition / synonym checks -------------
    children = defaultdict(set)
    for s_, o_ in g.subject_objects(RDFS.subClassOf):
        if isinstance(s_, URIRef) and isinstance(o_, URIRef):
            children[o_].add(s_)

    by_label = defaultdict(list)
    for c in classes:
        by_label[label[c].strip().lower()].append(c)

    def descendants(root):
        seen, stack = {root}, [root]
        while stack:
            for kid in children[stack.pop()]:
                if kid not in seen:
                    seen.add(kid); stack.append(kid)
        return seen

    exempt = set()
    for spec in args.exclude_branch:
        if spec.startswith("http"):
            roots = [URIRef(spec)]
        else:
            roots = by_label.get(spec.strip().lower(), [])
        if not roots:
            sys.exit(f"ERROR: --exclude-branch {spec!r} matched no class.")
        if len(roots) > 1:
            sys.exit(f"ERROR: --exclude-branch {spec!r} is ambiguous "
                     f"({len(roots)} classes share that label). Pass the IRI instead.")
        sub = descendants(roots[0])
        exempt |= sub
        print(f"\nexempt branch: {label[roots[0]]!r} -> {len(sub)} classes "
              f"({len(sub & approved)} of them approved)")

    print(f"\nclasses: {len(classes)}   approved: {len(approved)}")
    if no_status:
        print(f"\n!! {len(no_status)} classes have NO status value at all:")
        for c in sorted(no_status, key=lambda x: label[x])[:20]:
            print(f"   {label[c]}")
        if len(no_status) > 20:
            print(f"   ... and {len(no_status)-20} more")

    if bad_status:
        print(f"\n!! {len(bad_status)} classes have a status outside "
              f"{sorted(ALLOWED)}:")
        for c, v in sorted(bad_status, key=lambda t: label[t[0]])[:20]:
            print(f"   {label[c][:50]:<50} {v!r}")

    if multi_status:
        print(f"\n!! {len(multi_status)} classes carry MORE THAN ONE status value "
              f"(first alphabetically is used below):")
        for c, v in multi_status[:20]:
            print(f"   {label[c][:44]:<44} {v}")

    print("\nstatus values present:")
    for k, n in Counter(status.values()).most_common():
        print(f"   {str(k)!r:<22} {n}")

    checked = approved - exempt
    no_def = sorted((c for c in checked if not values(c, def_props)),
                    key=lambda c: label[c])
    no_syn = sorted((c for c in checked if not values(c, syn_props)),
                    key=lambda c: label[c])
    bad_parent = sorted(
        ((c, p) for c in approved for p in parents[c] if status.get(p) != TARGET),
        key=lambda t: label[t[0]])

    def write(rows, suffix, header, fmt):
        path = f"{args.out_prefix}_{suffix}.tsv"
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(header + "\n")
            for r in rows:
                fh.write(fmt(r) + "\n")
        print(f"   {len(rows):>5}  -> {path}")

    if exempt:
        print(f"\napproved concepts checked for definition/synonym: {len(checked)} "
              f"({len(approved & exempt)} exempted)")
    print("\nresults")
    # The two "missing" files are worksheets: fill in the proposed_* columns and
    # feed the file straight to insert_definitions.py.
    def cell(vals):
        return " ; ".join(" ".join(v.split()) for v in sorted(set(vals)))

    worksheet_header = ("iri\tlabel\texisting_definition\texisting_synonyms\t"
                        "proposed_definition\tproposed_new_synonyms")

    def worksheet_row(c):
        return (f"{c}\t{label[c]}\t{cell(values(c, def_props))}\t"
                f"{cell(values(c, syn_props))}\t\t")

    write(no_def, "missing_definition", worksheet_header, worksheet_row)
    write(no_syn, "missing_synonym", worksheet_header, worksheet_row)
    write(bad_parent, "unapproved_parent",
          "child_iri\tchild_label\tparent_iri\tparent_label\tparent_status",
          lambda t: f"{t[0]}\t{label[t[0]]}\t{t[1]}\t{label.get(t[1],'?')}\t"
                    f"{status.get(t[1]) or '(none)'}")

    both = [c for c in no_def if c in set(no_syn)]
    print(f"\n   {len(both)} approved concepts have neither a definition nor a synonym")

    if no_status:
        write(no_status, "no_status", "iri\tlabel",
              lambda c: f"{c}\t{label[c]}")

    if bad_status:
        write(bad_status, "invalid_status", "iri\tlabel\tstatus_value",
              lambda t: f"{t[0]}\t{label[t[0]]}\t{t[1]}")

    if multi_status:
        write(multi_status, "multiple_status", "iri\tlabel\tstatus_values",
              lambda t: f"{t[0]}\t{label[t[0]]}\t{'; '.join(t[1])}")

    if bad_parent:
        print("\noffending parents, most frequent first:")
        for p, n in Counter(p for _, p in bad_parent).most_common(12):
            print(f"   {n:>4}x  {label.get(p,'?'):<40} [{status.get(p) or 'no status'}]")


if __name__ == "__main__":
    main()