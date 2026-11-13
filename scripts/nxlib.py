"""
Shared helpers for NucLex scripts that add terms to the ontology
(sync_ncit.py, sync_nucleon.py).

Conventions kept here:
  - annotation properties are found by rdfs:label, not by IRI
  - files are opened as UTF-8
  - new class identifiers come from the import range (EDITORIAL_POLICY.md 3.3),
    tracked in scripts/next_import_id.txt, so they can never collide with
    identifiers minted in Protege
"""

import re, sys
from collections import defaultdict
from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL, URIRef, Literal, Namespace

BASE = "https://nuclex.com/id/"
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
DCTERMS = Namespace("http://purl.org/dc/terms/")

PROTEGE_RANGE = (1, 19999)
IMPORT_RANGE = (20000, 79999)
CLASS_RE = re.compile(r"^" + re.escape(BASE) + r"NUCLEX_(\d{7})$")

SCRIPTS = Path(__file__).resolve().parent
NEXT_IMPORT_ID_FILE = SCRIPTS / "next_import_id.txt"


def load(path):
    g = rdflib.Graph()
    with open(path, encoding="utf-8") as fh:
        g.parse(fh, format="xml", publicID=Path(path).resolve().as_uri())
    return g


def save(g, path):
    g.bind("nx", Namespace(BASE))
    g.bind("skos", SKOS)
    g.bind("oboInOwl", OBOINOWL)
    g.bind("dcterms", DCTERMS)
    g.serialize(destination=str(path), format="pretty-xml", encoding="utf-8")


def norm(name):
    return " ".join(str(name).replace("_", " ").lower().split())


def prop_by_label(g, name, required=True):
    """Annotation property whose rdfs:label is `name` (spaces/underscores alike)."""
    for p in sorted(g.subjects(RDF.type, OWL.AnnotationProperty)):
        for l in g.objects(p, RDFS.label):
            if norm(l) == norm(name):
                return p
    if required:
        sys.exit(f"ERROR: no annotation property labelled {name!r} in the ontology.")
    return None


def ensure_prop(g, local_name, label, definition):
    """Return the annotation property labelled `label`, declaring it if absent."""
    p = prop_by_label(g, label, required=False)
    if p is not None:
        return p, False
    p = URIRef(BASE + local_name)
    g.add((p, RDF.type, OWL.AnnotationProperty))
    g.add((p, RDFS.label, Literal(label)))
    g.add((p, SKOS.definition, Literal(definition)))
    g.add((p, OBOINOWL.id, Literal("nx:" + local_name)))
    return p, True


def label(g, c):
    ls = sorted(str(l) for l in g.objects(c, RDFS.label))
    return ls[0] if ls else "(no label)"


def class_by_label(g, text):
    hits = [c for c in g.subjects(RDF.type, OWL.Class) if label(g, c) == text]
    if len(hits) != 1:
        sys.exit(f"ERROR: expected one class labelled {text!r}, found {len(hits)}.")
    return hits[0]


def descendants(g, root):
    kids = defaultdict(set)
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            kids[o].add(s)
    seen, stack = {root}, [root]
    while stack:
        for k in kids[stack.pop()]:
            if k not in seen:
                seen.add(k)
                stack.append(k)
    return seen


def read_skip_file(path):
    """One code per line; text after # is a comment."""
    p = Path(path)
    if not p.exists():
        return set()
    out = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        code = line.split("#", 1)[0].strip()
        if code:
            out.add(code)
    return out


class Minter:
    """Hands out identifiers from the import range.

    Starts at whichever is higher: scripts/next_import_id.txt, or one past the
    highest import-range identifier already in the ontology. Call commit() only
    after the output file has been written.
    """

    def __init__(self, g):
        lo, hi = IMPORT_RANGE
        used = [int(m.group(1)) for s in g.subjects(RDF.type, OWL.Class)
                for m in [CLASS_RE.match(str(s))] if m and lo <= int(m.group(1)) <= hi]
        start = max(used) + 1 if used else lo
        if NEXT_IMPORT_ID_FILE.exists():
            m = re.search(r"(\d+)\s*$", NEXT_IMPORT_ID_FILE.read_text(encoding="utf-8"))
            if m:
                start = max(start, int(m.group(1)))
        self.next = start
        self.first = start

    def mint(self):
        if self.next > IMPORT_RANGE[1]:
            sys.exit("ERROR: import identifier range exhausted.")
        n = self.next
        self.next += 1
        return URIRef(f"{BASE}NUCLEX_{n:07d}"), f"NUCLEX:{n:07d}"

    def commit(self):
        if self.next != self.first:
            NEXT_IMPORT_ID_FILE.write_text(f"NUCLEX_{self.next:07d}\n", encoding="utf-8")


def add_class(g, minter, lab, parents, status_prop, status, extra=()):
    """Create a class; `extra` is an iterable of (property, value) pairs."""
    iri, curie = minter.mint()
    g.add((iri, RDF.type, OWL.Class))
    g.add((iri, RDFS.label, Literal(lab)))
    g.add((iri, OBOINOWL.id, Literal(curie)))
    for p in parents:
        g.add((iri, RDFS.subClassOf, p))
    g.add((iri, status_prop, Literal(status)))
    for p, v in extra:
        g.add((iri, p, v if isinstance(v, (URIRef, Literal)) else Literal(v)))
    return iri


def write_report(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(header) + "\n")
        for r in rows:
            fh.write("\t".join(" ".join(str(x).split()) for x in r) + "\n")
