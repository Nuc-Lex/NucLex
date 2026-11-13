# Changelog

All notable changes to NucLex are recorded here.

NucLex follows [semantic versioning](https://semver.org/):
**patch** for corrections, **minor** for new terms and branches,
**major** for structural change that requires users to update their data.

Each release is permanently archived at its version IRI.

---

## [Unreleased]

### Added

### Changed

### Deprecated

---

## [1.0.0] — 2026-11-13

First stable release. Identifiers are now persistent.

### Added

- 1,583 classes covering nuclear medicine procedures, radiopharmaceuticals,
  radionuclides, instrumentation, image acquisition, quantitative measurement,
  dosimetry, and the underlying physical processes
- `physical and biological process` branch: radiation interactions, nuclear
  processes, detection physics, image formation phenomena
- Radiopharmaceuticals inherited from the NCI Thesaurus (version 26.10d),
  under `radiopharmaceutical compound`
- Radionuclides mapped to NUCLEON, the Nuclide and Element Ontology, including
  every unstable nuclide with a DICOM code (CID 18 and CID 4020)
- 15 object properties and 10 cross-reference annotation properties
- Definitions for all terms outside the `radiopharmaceutical compound` branch
- Cross-references to SNOMED CT, NCI Thesaurus, UMLS, RadLex, LOINC,
  RSNA Playbook, IBSI, DICOM, and NUCLEON

### Changed (from the 0.x beta versions)

- Top-level classes realigned to SNOMED CT hierarchies
- All identifiers reminted to `https://nuclex.com/id/NUCLEX_NNNNNNN`
- Definitions and synonyms moved to `skos:definition` and `skos:altLabel`

[Unreleased]: https://github.com/Nuc-Lex/NucLex/compare/v1.0.0...HEAD
[1.0.0]: https://nuclex.com/releases/1.0.0/nuclex.owl
