#!/usr/bin/env python3
# =============================================================================
# RETIRED - DO NOT RUN.
# This performed the one-time identifier migration before NucLex 1.0.0.
# Running it again would renumber every class AND the readable property IRIs,
# breaking every published identifier. Kept for reference only.
# =============================================================================
"""
NucLex IRI remint.

Assigns a fresh NUCLEX IRI to every entity in the ontology, except entities
that belong to external vocabularies (SKOS, OBO, W3C, Dublin Core...), which
are left untouched.

Usage:
    python3 remint.py INPUT.owl --version 1.0.0 [--out nuclex.owl]

Outputs:
    nuclex.owl                    the reminted ontology   (--out to change)
    nuclex-1.0.0-id-mapping.tsv   old IRI -> new IRI, for your audit trail
"""

import sys, re, argparse
from collections import defaultdict
import rdflib
from rdflib import RDF, RDFS, OWL, URIRef, Literal

NEW_BASE     = "https://nuclex.com/id/"
PREFIX       = "NUCLEX_"
CURIE_PFX    = "NUCLEX:"
WIDTH        = 7
START        = 1
ONTOLOGY_IRI = "https://nuclex.com/nuclex.owl"
RELEASE_BASE = "https://nuclex.com/releases/"

# Entities in these namespaces belong to someone else. Everything else is ours.
EXTERNAL = (
    "http://www.w3.org/",                            # rdf, rdfs, owl, xsd, skos
    "http://purl.org/dc/",                           # dc, dcterms
    "http://purl.obolibrary.org/obo/",               # BFO, IAO, RO, ChEBI...
    "http://www.geneontology.org/formats/oboInOwl#", # oboInOwl
    "http://xmlns.com/foaf/",
    "http://snomed.info/",
    "http://loinc.org",
    "https://w3id.org/sssom/",
)

OBO_ID = URIRef("http://www.geneontology.org/formats/oboInOwl#id")
ENTITY_TYPES = [OWL.Class, OWL.ObjectProperty, OWL.AnnotationProperty,
                OWL.DatatypeProperty, OWL.NamedIndividual]


def is_external(iri: str) -> bool:
    return iri.startswith(EXTERNAL)


def sort_key(iri: str):
    """Keep existing numeric order where one exists so the diff is readable."""
    m = re.search(r'(\d+)\s*$', iri)
    return (0, int(m.group(1)), "") if m else (1, 0, iri)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--version", required=True, help="release version, e.g. 1.0.0")
    ap.add_argument("--out", default="nuclex.owl")
    args = ap.parse_args()

    g = rdflib.Graph()
    g.parse(args.input)
    print(f"read {len(g)} triples from {args.input}")

    # ---- 1. every declared entity that is not external --------------------
    entities, skipped = set(), set()
    for t in ENTITY_TYPES:
        for s in g.subjects(RDF.type, t):
            if not isinstance(s, URIRef):
                continue
            (skipped if is_external(str(s)) else entities).add(str(s))

    # anything NucLex-shaped that is used but never declared
    declared = entities | skipped
    for s, p, o in g:
        for term in (s, p, o):
            if isinstance(term, URIRef) and str(term) not in declared \
               and not is_external(str(term)) and str(term) != ONTOLOGY_IRI:
                entities.add(str(term))

    print(f"entities to remint : {len(entities)}")
    print(f"external, untouched: {len(skipped)}")
    for e in sorted(skipped):
        print("    ", e)

    # ---- 2. assign ---------------------------------------------------------
    ordered = sorted(entities, key=sort_key)
    mapping = {old: f"{NEW_BASE}{PREFIX}{str(i).zfill(WIDTH)}"
               for i, old in enumerate(ordered, start=START)}

    # ---- 3. rebuild with IRIs swapped in every triple position -------------
    def swap(term):
        return URIRef(mapping[str(term)]) if isinstance(term, URIRef) \
               and str(term) in mapping else term

    new = rdflib.Graph()
    for pfx, ns in g.namespaces():
        new.bind(pfx, ns)
    new.bind("NUCLEX", NEW_BASE + PREFIX)
    for s, p, o in g:
        new.add((swap(s), swap(p), swap(o)))

    # ---- 4. oboInOwl:id -> the new ID. Old IDs are NOT retained. -----------
    for newiri in mapping.values():
        subj = URIRef(newiri)
        for stale in list(new.objects(subj, OBO_ID)):
            new.remove((subj, OBO_ID, stale))
        local = newiri.rsplit("/", 1)[-1].replace(PREFIX, "")
        new.add((subj, OBO_ID, Literal(f"{CURIE_PFX}{local}")))

    # ---- 5. version --------------------------------------------------------
    ont = URIRef(ONTOLOGY_IRI)
    if (ont, RDF.type, OWL.Ontology) in new:
        for pred in (OWL.versionIRI, OWL.versionInfo):
            for v in list(new.objects(ont, pred)):
                new.remove((ont, pred, v))
        new.add((ont, OWL.versionIRI,
                 URIRef(f"{RELEASE_BASE}{args.version}/nuclex.owl")))
        new.add((ont, OWL.versionInfo, Literal(args.version)))
    else:
        print("\n  WARNING: no owl:Ontology declaration — header not updated.")

    # ---- 6. write ----------------------------------------------------------
    mapfile = f"nuclex-{args.version}-id-mapping.tsv"
    new.serialize(destination=args.out, format="pretty-xml")
    with open(mapfile, "w", encoding="utf-8", newline="") as fh:
        fh.write("old_iri\tnew_iri\tlabel\n")
        for old in ordered:
            lb = list(new.objects(URIRef(mapping[old]), RDFS.label))
            fh.write(f"{old}\t{mapping[old]}\t{lb[0] if lb else ''}\n")

    print(f"\nwrote {len(new)} triples -> {args.out}")
    print(f"wrote mapping           -> {mapfile}")
    print(f"version IRI             -> {RELEASE_BASE}{args.version}/nuclex.owl")
    print(f"NEXT FREE ID            -> {PREFIX}{str(START+len(mapping)).zfill(WIDTH)}")

    # ---- 7. verify ---------------------------------------------------------
    bad = {str(t) for s, p, o in new for t in (s, p, o)
           if isinstance(t, URIRef) and not is_external(str(t))
           and not str(t).startswith(NEW_BASE)
           and not str(t).startswith("https://nuclex.com/")}
    print(f"\nVERIFY un-reminted NucLex IRIs remaining: {len(bad)}")
    for b in sorted(bad)[:10]:
        print("   ", b)


if __name__ == "__main__":
    main()
