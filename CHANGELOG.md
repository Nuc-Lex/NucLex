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

## [1.0.0] — 2026-11-12

First stable release. Identifiers are now persistent.

### Added

- Initial release of NNNN classes covering nuclear medicine procedures,
  radiopharmaceuticals, instrumentation, image acquisition, quantitative
  measurement, dosimetry, and the underlying physical processes
- `physical and biological process` branch: radiation interactions, nuclear
  processes, detection physics, image formation phenomena
- NN object properties and NN annotation properties
- Definitions for all terms outside the `Radioconjugate` branch
- Cross-references to SNOMED CT, NCI Thesaurus, UMLS, RadLex, LOINC,
  RSNA Playbook, IBSI, DICOM

### Changed

- Top-level classes realigned to SNOMED CT hierarchies
- All identifiers reminted to `https://nuclex.com/id/NUCLEX_NNNNNNN`
- Definitions and synonyms moved to `skos:definition` and `skos:altLabel`

[Unreleased]: https://github.com/.../compare/v1.0.0...HEAD
[1.0.0]: https://nuclex.com/releases/1.0.0/nuclex.owl