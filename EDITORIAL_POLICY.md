# NucLex Editorial Policy

**Version 1.0.0 — November 2026**

This document governs how NucLex is built and maintained. It is the reference for
anyone adding, editing, or approving a term.

---

## 1. Goal and scope

### 1.1 Goal

NucLex serves as the foundational semantic infrastructure for modern nuclear
medicine clinical practice and research.

### 1.2 What NucLex covers

- Nuclear medicine, theranostics, and molecular imaging procedures
- Radiopharmaceuticals and radionuclides (inherited from NCI Thesaurus and NUCLEON, respectively)
- Imaging devices, detectors, and their components
- Image acquisition, reconstruction, and processing
- Quantitative imaging measurements and image-derived features
- Dosimetry and computational nuclear oncology
- The physical and biological processes underlying the above

### 1.3 What NucLex does not cover

These are out of scope by decision:

- **Clinical indications.** NucLex does not record which conditions an agent is
  approved or used to treat.
- **Patient-level data.** NucLex contains classes only, not individual instances of those classes.
- **Anatomy, disease, and organism terminology** beyond the minimum needed to
  describe nuclear medicine practice. Map to SNOMED CT or UBERON instead.

### 1.4 Contents

NucLex contains classes, object properties, and annotation properties. 

---

## 2. Governance and approval

### 2.1 Consensus threshold

During the early stage of NucLex, acceptance of any new or modified term requires
agreement from 3 of 4 (75%) subject matter experts (SMEs).

Terms that are strictly organizational terms (i.e., created only to structure the
hierarchy) do not require secondary SME approval.

SMEs are assigned a unique identifier, and each term that is approved must list
the SME IDs in the `approver id` field. Curation metadata (`approver id`,
`assigned to`, and `status`) is removed from public releases.

### 2.2 Status values

Every class carries exactly one `status` value. Only three values are permitted:

| Value | Meaning |
|---|---|
| `draft` | A placeholder or exploratory entry. Not yet complete. |
| `needs approval` | Complete and awaiting review by subject matter experts. |
| `approved` | Has passed review. |

A class with no status, more than one status, or a value outside this list is an
error. `scripts/find_problematic_terms.py` checks for all three.

### 2.3 Moving a term to `needs approval`

A term is ready for review when it has:

- A label meeting the criteria in section 4
- A definition meeting the criteria in section 5
- A parent that is itself at least `needs approval`
- Synonyms, if any exist (section 6)

### 2.4 Moving a term to `approved`

Approval is recorded by setting `status` to `approved` and entering the reviewer's
identifier in `approver id`. 

### 2.5 Parent approval

A term may not be `approved` while its parent is not. Approving a leaf term whose
grouping parent is still `draft` leaves the hierarchy in an inconsistent state, and
the QC script reports it.

---

## 3. Identifiers

### 3.1 Pattern

Classes use the following pattern for identifiers:
```
IRI     https://nuclex.com/id/NUCLEX_0000186
CURIE   NUCLEX:0000186
```

Seven digits, zero-padded. Identifiers are opaque. They encode no meaning, no 
hierarchy position, no creation date, and no status. A term's label may change 
freely; its identifier never does.

Object and annotation properties use readable identifiers rather than numeric ones. 
```
IRI     https://nuclex.com/id/assigned_to
CURIE   nx:assigned_to
```


### 3.2 Identifiers never reused

An identifier, once assigned, is never assigned to anything else. This holds even
for a term deleted before it was ever released. Gaps in the numbering are permanent
and must never be filled in.

### 3.3 Minting identifiers

Identifiers are minted from assigned ranges so that two editors cannot collide:

| Source | Range |
|---|---|
| Primary editor, in Protégé | 1 – 19 999 |
| Automated imports (`sync_ncit.py`, `sync_nucleon.py`) | 20 000 – 79 999 |
| Additional curators | assigned on joining |

Each range has its own counter: `scripts/next_id.txt` for Protégé and
`scripts/next_import_id.txt` for the import scripts, which update it themselves.
The next free identifier for Protégé is recorded in `scripts/next_id.txt`. Protégé's
identifier counter lives in local user preferences, not in the ontology file, so
it must be set by hand to that value, and reset after any bulk operation that
mints identifiers outside Protégé. `scripts/check_ids.py` reports the highest
identifier in use and warns if `next_id.txt` has fallen behind. See `WORKFLOW.md`.

### 3.4 Retirement

Retired classes are never deleted. They are marked `owl:deprecated` so that
historical data referencing them remains valid. Where a replacement exists, it is
recorded with `dcterms:isReplacedBy`.

An identifier present in a published release must never disappear from a later one.


---

## 4. Labels

### 4.1 Selecting the preferred term

When determining the `rdfs:label`, ask, in order:

1. Is the term as self-explanatory as possible without relying on the ontology
   hierarchy to define it? (`image rows` is preferred over `rows`.)
2. Does the term sufficiently and unambiguously describe the underlying concept?
3. Is the term broadly used and understood in the field?
4. Has the term been adopted as official by another standard-setting organization?

### 4.2 Form

- Lowercase, except for proper nouns and established capitalizations
  (`Compton scattering`, `Curie score`)
- Singular, not plural
- No trailing or doubled whitespace
- Trade names and brand names are synonyms, never the primary label.
- Avoid acronyms (`positron emission tomography` instead of `PET`) as the label. 
  Acronyms should instead be listed under synonyms.

### 4.3 Uniqueness

No two classes may share a label. Labels are case-sensitive: `K1` and `k1` are
distinct terms in kinetic modelling. A duplicate label indicates
either a duplicate concept or an identifier collision. `scripts/check_ids.py`
checks for this.

---

## 5. Definitions

### 5.1 Requirement

Every approved class must carry a `skos:definition`.

**Exception:** classes in the `radiopharmaceutical compound` branch (section 10)
are currently exempt, as their content derives from the NCI Thesaurus without
definitions. The QC script skips this branch for the definition and synonym
checks.

### 5.2 Form

A definition answers "what is X?" in a single noun phrase.

- Usually begins with `A`, `An`, or `The`
- Ends with a period
- Does not restate the term's own distinguishing words
- Generally, should not include examples of how the thing is used or applied

### 5.3 Non-circularity

A definition may use the genus (`An image reconstructed from…`) but must not reuse
the term's distinguishing words.

| Term | Not acceptable | Acceptable |
|---|---|---|
| gated acquisition | An acquisition that is gated. | An acquisition in which data are sorted into bins according to the phase of a physiological cycle. |
| radiation measurement device| A device that measures radiation. | A manufactured instrument engineered to detect, quantify, or characterize ionizing radiation. |

### 5.4 Sources

Where a definition derives from a published source, record it. Preferred sources
for nuclear medicine physics are ICRU reports, the ICRP Glossary, and the IAEA
Nuclear Safety and Security Glossary.

---

## 6. Synonyms

Record synonyms as `skos:altLabel`. Add one wherever a term is known by another
name in practice.

Include:

- Trade and brand names
- Research and development codes
- Abbreviations and acronyms
- Alternative spellings, including British and American variants
- Older names still in circulation

Do not include:

- A string that is the label of a different class
- Definitions, descriptions, or any other prose

Where no synonym exists, the field is simply absent. A term is not held back from
approval for lack of a synonym.

---

## 7. Cross-references

### 7.1 Principle

NucLex terms should be mapped to existing ontologies and terminologies whenever a
corresponding term exists. The match may be exact or approximate; it is not a claim 
that the two concepts are identical.

### 7.2 Properties

| Property | Source |
|---|---|
| `snomedct_id` | SNOMED CT |
| `ncit_id` | NCI Thesaurus |
| `umls_cui` | UMLS Metathesaurus |
| `radlex_id` | RadLex |
| `loinc_id` | LOINC |
| `playbook_id` | RSNA Playbook |
| `ibsi_id` | Image Biomarker Standardisation Initiative manual |
| `dicom_tag` | DICOM group and element number |
| `obo_id` | OBO Foundry ontologies |
| `nucleon_id` | NUCLEON (Nuclide and Element Ontology) |

### 7.3 Format

One code per annotation. A term with two SNOMED codes carries two `snomedct_id`
matches.

Use a consistent form for IRI/URLs across the ontology. Values must not mix resolution URLs
from different providers for the same source.

### 7.4 Licensing

NucLex records external **codes** as cross-references. It does not copy external
**descriptions** — labels, synonyms, or definitions — from sources whose licence
does not permit redistribution. This applies in particular to SNOMED CT.

NCI Thesaurus content is US Government work and may be reused freely.

---

## 8. Hierarchy

### 8.1 Upper level

All NucLex top-level classes should correspond to top-level classes in SNOMED CT.

**Exception:** where SNOMED CT has no suitable hierarchy, NucLex may declare its
own. Each such branch must be documented in rdfs:comment with its inclusion reason and 
an explanation of why no SNOMED hierarchy fits. The `physical and biological process`
branch is the current instance, covering radiation interactions, nuclear processes,
detection physics, and radiobiology, none of which fall within SNOMED's scope.

### 8.2 Multiple inheritance

A class normally has one parent. Multiple parents are permitted but should
be deliberate, not accidental.

### 8.3 Avoid redundant layers

Do not create a class whose only child is a near-synonym of itself. If a grouping
class has exactly one child, question whether both are needed.

---

## 9. Noun or property?

When deciding if a highly specific concept should be either a combined noun + adjective (eg, `pinhole 
collimator`) or separate noun and property classes (e.g., `collimator` in the objects branch and 
`collimator type / pinhole` in the properties branch) follow these three tests.

### Test 1 — Different properties (most important)

*Does this more specific thing need different properties than its parent?*

A pinhole collimator has an aperture diameter and a focal length. A parallel hole
collimator has a septal thickness and a hole diameter. These are different,
non-overlapping properties, indicating the need for `pinhole collimator` as a class.

### Test 2 — Combinatorial explosion

*Will this property combine with other properties in many combinations?*

Collimators vary by geometry (parallel hole, pinhole, fan beam), by energy rating
(low, medium, high), and by performance class (general purpose, high resolution,
high sensitivity). Creating a subclass per combination gives
`LowEnergyHighResolutionParallelHoleCollimator` and dozens like it.

**Therefore: descriptive attributes like `low energy` and `general purpose` are
properties, not subclasses.**

### Test 3 — Fundamental kind

*Is this adjective a fundamental kind of thing, or a descriptive attribute?*

`Parallel hole` describes a physical structure — it is a kind of collimator.
`Low energy` describes a performance rating — it is an attribute of one.

**Therefore: `parallel hole collimator` is a subclass; energy rating is a
property.**

---

## 10. Inherited branches: radiopharmaceuticals and radionuclides

### 10.1 Radiopharmaceuticals (NCI Thesaurus)

The `radiopharmaceutical compound` branch is inherited from the NCI Thesaurus
(NCIt C1446) and brought up to date before each release with
`scripts/sync_ncit.py`. Terms are matched on `ncit_id`.

- New NCIt concepts are added with a new NucLex identifier, their NCIt label and
  synonyms, `ncit_id`, and UMLS CUI, under their NCIt parent, with status
  `approved`.
- NCIt definitions are not imported: they often state clinical indications,
  which are out of scope (section 1.3).
- When NCIt renames a concept, the NucLex label follows the new NCIt name and
  the previous label is kept as a synonym.
- Nothing else about an existing term is changed by the sync: not its
  identifier, synonyms, or position. NucLex's own grouping classes in this
  branch are untouched, and new concepts are not added to them automatically.
- Concepts NCIt has retired, or moved out of the branch, are reported. An editor
  decides whether to mark them `owl:deprecated` (section 3.4).
- A rejected NCIt concept is listed in `scripts/ncit_skip.txt` so it is not
  re-added at the next sync.

Preferred names for common radiopharmaceuticals will be modified to follow the
nomenclature guidelines of the European Association of Nuclear Medicine (EANM)
Working Group on Nomenclature in Radiopharmaceutical Chemistry. Where a preferred
name is changed, the previous name is retained as a synonym, and the NCIt code is
listed in `scripts/ncit_keep_labels.txt` so the sync does not revert it.

### 10.2 Radionuclides (NUCLEON)

Radionuclides are mapped to NUCLEON, RSNA's Nuclide and Element Ontology, with
`scripts/sync_nucleon.py`.

- Every class in the `radionuclide` branch records its NUCLEON IRI in
  `nucleon_id`.
- Unstable nuclides that carry a DICOM code in NUCLEON (DICOM CID 18 and CID
  4020) are included in NucLex.
- Only the nuclide's name is inherited: the label (`Lutetium-177`) and the
  symbol as a synonym (`Lu-177`). NUCLEON's physical data (half-lives, decay
  modes, emissions) are not copied; NUCLEON is licensed CC BY-NC-ND 4.0, and
  `nucleon_id` gives users the route to it.
- The definition of an imported radionuclide is generated from its mass number,
  atomic number, and half-life, e.g. *"An unstable nuclide with 177 nucleons and
  71 protons, with a half-life of 6.6443 days."*

---

## 11. Versioning and release

### 11.1 Semantic versioning

NucLex uses MAJOR.MINOR.PATCH.

| Release | Contains |
|---|---|
| **Patch** (1.0.1) | Corrects errors, typos, or minor classification fixes |
| **Minor** (1.1.0) | Adds new branches or concepts without breaking existing logic |
| **Major** (2.0.0) | Structural refactoring, or large-scale retirement or merging that requires users to update their data |

Version 1.0.0 marks the first stable public release. These rules apply from that
point onward.

### 11.2 Format

The definitive version of NucLex is maintained and published in OWL.

### 11.3 Version identifiers

```
Ontology IRI    https://nuclex.com/nuclex.owl
Version IRI     https://nuclex.com/releases/1.0.0/nuclex.owl
```

Every release is archived at its version IRI and remains there permanently. A
frozen copy is also kept in this repository at `releases/X.Y.Z/nuclex.owl`, and
is the reference against which the next release is checked.

### 11.4 Release notes

All changes between versions are documented in a publicly accessible release notes
file: terms added, terms changed, terms deprecated.

### 11.5 Release requirements

A release may be published only when:

1. The QC script reports no approved term under an unapproved parent, and no
   class with a missing, invalid, or duplicated status.
2. The ID check against the previous release reports no missing identifiers.
   Changed labels are allowed (section 3.1) but each must be reviewed and
   intended.
3. The ontology header carries the correct version IRI, version info, and
   modification date, along with the title, description, and licence.
4. No curation metadata (`approver id`, `assigned to`, `status`) remains in the
   released file, and no unapproved class is included.
5. The release is archived at its version IRI and in `releases/X.Y.Z/`.
6. The release notes (`CHANGELOG.md`) are updated.
7. `scripts/next_id.txt` records the next free identifier.

The step-by-step procedure, with commands, is in `WORKFLOW.md`.

---

## 12. Licensing

NucLex is released under **Creative Commons Attribution 4.0 International
(CC BY 4.0)**.

The licence is declared in the ontology header and in a `LICENSE` file distributed
with the ontology.

---

## Appendix — quality checks

| Check | Finds | Script | Blocks release? |
|---|---|---|---|
| Missing definition | Approved terms with no `skos:definition` (section 5.1 exception applies) | `find_problematic_terms.py` | Should be resolved |
| Missing synonym | Approved terms with no `skos:altLabel` | `find_problematic_terms.py` | No — advisory (section 6) |
| Unapproved parent | Approved terms whose parent is not approved | `find_problematic_terms.py` | **Yes** |
| No status | Classes carrying no `status` value | `find_problematic_terms.py` | **Yes** |
| Invalid status | Classes with a `status` outside the three permitted values | `find_problematic_terms.py` | **Yes** |
| Multiple status | Classes carrying more than one `status` value | `find_problematic_terms.py`, `check_ids.py` | **Yes** |
| Duplicate label | Two classes sharing a label | `check_ids.py` | **Yes** |
| Multiple labels | One class with two labels — an identifier collision | `check_ids.py` | **Yes** |
| Malformed IRI | A class or property outside the NucLex identifier pattern | `check_ids.py` | **Yes** |
| `next_id.txt` behind | The recorded next identifier is already in use | `check_ids.py` | **Yes** |
| Missing since release | A published identifier that has disappeared | `check_ids.py --previous` | **Yes** |
| Changed label since release | An identifier whose label has changed | `check_ids.py --previous` | No — review each one |
