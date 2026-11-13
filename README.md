# NucLex: The Nuclear Medicine Lexicon

**NucLex is a formal, community-driven ontology for the domain of nuclear
medicine.**

NucLex was initiated by the SNMMI AI Task Force and is developed and maintained by
the NucLex Committee, led by Dr. Tyler Bradshaw and Dr. Babak Saboury. 
It is published by the Institute of Nuclear Medicine.

This repository contains the official Web Ontology Language (OWL) files for NucLex.
The goal is a standardized, computable vocabulary for nuclear medicine and 
theranostics concepts.

---

## Current release

| | |
|---|---|
| **Version** | 1.0.0 |
| **File** | `nuclex.owl` |
| **Ontology IRI** | `https://nuclex.com/nuclex.owl` |
| **Version IRI** | `https://nuclex.com/releases/1.0.0/nuclex.owl` |
| **Format** | OWL (RDF/XML) |
| **Licence** | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

Version 1.0.0 is the first stable release. Terms and identifiers are now
persistent: an identifier, once published, is never reused or removed.

---

## Using NucLex

### Browsing

The easiest way to explore NucLex is with
[Protégé](https://protege.stanford.edu/), a free, open-source ontology editor:

1. Download and install
   [Protégé Desktop](https://protege.stanford.edu/products.php#desktop-protege)
2. Clone this repository or download `nuclex.owl`
3. Open `nuclex.owl` in Protégé

### Identifiers

Every NucLex term has a persistent identifier:

```
IRI     https://nuclex.com/id/NUCLEX_0000186
CURIE   NUCLEX:0000186
```

Identifiers are opaque — they encode no meaning and never change, even when a
label does. Retired terms are marked `owl:deprecated` rather than deleted, so
existing references stay valid.

Object and annotation properties use readable identifiers instead, for example
`https://nuclex.com/id/status`.

### Versioning

NucLex follows semantic versioning:

- **Patch** (1.0.1) — corrections, typos, minor classification fixes
- **Minor** (1.1.0) — new branches or concepts, no breaking changes
- **Major** (2.0.0) — structural refactoring or large-scale retirement

Each release is permanently archived at its version IRI. Changes between releases
are recorded in `CHANGELOG.md`.

---

## Contributing

NucLex is in active development and we welcome collaborators, reviewers, and
contributors.

Before proposing a term, please read `EDITORIAL_POLICY.md`. It covers what belongs
in NucLex, how labels and definitions are written, the approval workflow, and how
identifiers are managed.

Maintainers: the procedure for editing the ontology, running the quality checks,
and building a release is in `WORKFLOW.md`.

New and modified terms require agreement from 3 of 4 subject matter experts.

To report a problem or propose a term, open an issue in this repository.

---

## Licence

NucLex is released under
[Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

Cross-references to external terminologies record codes only. NucLex does not
redistribute content from terminologies whose licence does not permit it.