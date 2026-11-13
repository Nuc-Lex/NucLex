#!/usr/bin/env python3
"""
Bring the radiopharmaceutical branch up to date with the NCI Thesaurus.

Fetches every descendant of NCIt C1446 (Radiopharmaceutical Compound) from the
NCI EVS REST API and compares it with NucLex, matching on ncit_id.

  - NCIt concepts not yet in NucLex are added: label, synonyms, ncit_id, UMLS
    CUI, placed under their NCIt parent. They get a new identifier from the
    import range. NCIt definitions are NOT imported (they often state clinical
    indications, which are out of scope).
  - Existing terms whose NCIt name has changed are relabelled to the NCIt name,
    and the old label is kept as a synonym (skos:altLabel). Exception: codes
    listed in scripts/ncit_keep_labels.txt, whose NucLex label is a deliberate
    choice (e.g. EANM nomenclature, policy section 10), are left alone.
    --no-update-labels reports name changes without applying them.
  - Nothing else about an existing term is changed: not its identifier,
    synonyms, or position. NucLex's own grouping classes are never touched.
  - Reported for a person to decide on, not changed automatically:
      retired   - NCIt has retired the concept: mark it owl:deprecated
      moved     - still active in NCIt but no longer under C1446

Concepts listed in scripts/ncit_skip.txt are never added. Put a code there
when you reject a new concept, so it does not come back at the next sync.

Report actions: added, relabelled, label kept, retired, moved, skipped.

Writes a NEW ontology file and a report TSV. Never modifies the input.

Usage:
    python scripts/sync_ncit.py nuclex-source.owl --dry-run
    python scripts/sync_ncit.py nuclex-source.owl --out nuclex-source-ncit.owl
"""

import argparse, json, sys, time, urllib.request, urllib.error
from rdflib import Literal, URIRef, RDFS
import nxlib
from nxlib import SKOS

API = "https://api-evsrest.nci.nih.gov/api/v1"
NCIT_IRI = "http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#"


def get(path):
    url = API + path
    req = urllib.request.Request(url, headers={"User-Agent": "NucLex-sync"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                sys.exit(f"ERROR: could not reach the NCI EVS API ({url}): {e}")
            time.sleep(3)


def code_of(value):
    return str(value).rsplit("#", 1)[-1].strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ontology")
    ap.add_argument("--out", default="nuclex-source-ncit.owl")
    ap.add_argument("--report", default="ncit_sync_report.tsv")
    ap.add_argument("--root", default="C1446", help="NCIt root code (default C1446)")
    ap.add_argument("--status", default="approved", help="status for new terms")
    ap.add_argument("--skip-file", default=str(nxlib.SCRIPTS / "ncit_skip.txt"))
    ap.add_argument("--keep-labels-file",
                    default=str(nxlib.SCRIPTS / "ncit_keep_labels.txt"))
    ap.add_argument("--no-update-labels", action="store_true",
                    help="report NCIt name changes but do not apply them")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    g = nxlib.load(args.ontology)
    ncit_p = nxlib.prop_by_label(g, "ncit id")
    umls_p = nxlib.prop_by_label(g, "umls cui")
    status_p = nxlib.prop_by_label(g, "status")

    # NucLex side: every class with an ncit_id, anywhere in the ontology
    by_code = {}
    for c, v in g.subject_objects(ncit_p):
        by_code.setdefault(code_of(v), c)
    if args.root not in by_code:
        sys.exit(f"ERROR: no NucLex class has ncit_id {args.root}.")
    root = by_code[args.root]
    branch = nxlib.descendants(g, root)
    in_branch = {code_of(v): c for c in branch for v in g.objects(c, ncit_p)}
    print(f"NucLex: '{nxlib.label(g, root)}' branch has {len(branch)} classes, "
          f"{len(in_branch)} with an ncit_id")

    # NCIt side
    meta = get(f"/concept/ncit/{args.root}?include=minimal")
    print(f"NCIt:   version {meta.get('version')}, fetching descendants of {args.root}...")
    desc = get(f"/concept/ncit/{args.root}/descendants?maxLevel=10000&fromRecord=0&pageSize=10000")
    ncit_name = {d["code"]: d["name"] for d in desc}
    print(f"        {len(ncit_name)} descendants")

    skip = nxlib.read_skip_file(args.skip_file)
    report = []

    # ---- new concepts ----------------------------------------------------
    todo = sorted(c for c in ncit_name if c not in by_code and c not in skip)
    for c in sorted(set(ncit_name) & skip - set(by_code)):
        report.append(("skipped", "", c, "", ncit_name[c], "listed in skip file"))
    details = {c: get(f"/concept/ncit/{c}?include=synonyms,parents,properties") for c in todo}

    minter = nxlib.Minter(g)
    added = {}
    pending = list(todo)
    while pending:
        progress = False
        for c in list(pending):
            d = details[c]
            pcodes = [p["code"] for p in d.get("parents", [])]
            if any(p in todo and p not in added for p in pcodes):
                continue                       # add the parent first
            parents = [by_code.get(p) or added.get(p) for p in pcodes]
            parents = [p for p in parents if p is not None]
            note = ""
            if not parents:
                parents = [root]
                note = f"NCIt parent(s) {pcodes} not in NucLex; placed under root"
            name = d["name"]
            syns, seen = [], {name.lower()}
            for s in d.get("synonyms", []):
                if s.get("type") == "FULL_SYN" and s["name"].lower() not in seen:
                    seen.add(s["name"].lower())
                    syns.append(s["name"])
            extra = [(ncit_p, NCIT_IRI + c)]
            extra += [(umls_p, p["value"]) for p in d.get("properties", [])
                      if p.get("type") == "UMLS_CUI"]
            extra += [(SKOS.altLabel, s) for s in syns]
            iri = nxlib.add_class(g, minter, name, parents, status_p, args.status, extra)
            added[c] = iri
            report.append(("added", str(iri), c, name, name, note))
            pending.remove(c)
            progress = True
        if not progress:                       # a cycle; should not happen
            sys.exit(f"ERROR: could not place {pending}")

    # ---- existing terms that changed in NCIt -----------------------------
    keep = nxlib.read_skip_file(args.keep_labels_file)
    for c, cls in sorted(in_branch.items()):
        if c == args.root:
            continue
        old = nxlib.label(g, cls)
        if c not in ncit_name:
            info = get(f"/concept/ncit/{c}?include=minimal")
            if not info.get("active", True):
                report.append(("retired", str(cls), c, old, info.get("name", ""),
                               "retired in NCIt: mark owl:deprecated in Protege"))
            else:
                report.append(("moved", str(cls), c, old, info.get("name", ""),
                               f"no longer under {args.root} in NCIt"))
            continue
        new = " ".join(ncit_name[c].split())
        if " ".join(old.split()) == new:
            continue
        if c in keep:
            report.append(("label kept", str(cls), c, old, new,
                           "listed in ncit_keep_labels.txt"))
        elif args.no_update_labels:
            report.append(("label differs", str(cls), c, old, new,
                           "not applied (--no-update-labels)"))
        else:
            for l in list(g.objects(cls, RDFS.label)):
                g.remove((cls, RDFS.label, l))
            g.add((cls, RDFS.label, Literal(new)))
            have = {str(s).strip().lower() for s in g.objects(cls, SKOS.altLabel)}
            if old.strip().lower() not in have:
                g.add((cls, SKOS.altLabel, Literal(old)))
            for s in [x for x in g.objects(cls, SKOS.altLabel) if str(x).strip() == new]:
                g.remove((cls, SKOS.altLabel, s))  # the new label is no longer a synonym
            report.append(("relabelled", str(cls), c, old, new,
                           "old label kept as synonym"))

    # ---- output -----------------------------------------------------------
    counts = {}
    for r in report:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print("\nresult")
    for k in ("added", "relabelled", "label kept", "label differs", "retired",
              "moved", "skipped"):
        print(f"  {k:<14} {counts.get(k, 0)}")
    for r in report:
        if r[0] in ("added", "retired", "moved"):
            print(f"    {r[0]:<8} {r[2]:<8} {r[3] or r[4]}" + (f"   [{r[5]}]" if r[5] and r[0] == 'added' else ""))
        elif r[0] in ("relabelled", "label kept", "label differs"):
            print(f"    {r[0]:<14} {r[2]:<8} {r[3]!r} -> {r[4]!r}")

    nxlib.write_report(args.report, ("action", "nuclex_iri", "ncit_code", "nuclex_label",
                                     "ncit_name", "note"), report)
    print(f"\nreport -> {args.report}")
    if args.dry_run:
        print("DRY RUN - ontology not written.")
        return
    nxlib.save(g, args.out)
    minter.commit()
    print(f"wrote {args.out}")
    if added:
        print(f"next import identifier is now NUCLEX_{minter.next:07d} (scripts/next_import_id.txt)")


if __name__ == "__main__":
    main()
