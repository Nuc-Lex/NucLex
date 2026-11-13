# NucLex maintainer workflow

How to edit, check, and release NucLex. The rules behind these steps are in
`EDITORIAL_POLICY.md`.

**Only ever edit `nuclex-source.owl`.** `nuclex.owl` is generated at release time,
and the copies in `releases/` are frozen.

---

## 1. Editing the ontology

1. `git pull`
2. Check Protégé's ID counter matches `scripts/next_id.txt` (see [Protégé setup](#protégé-setup)).
3. Open `nuclex-source.owl` in Protégé and make your changes. Give every new
   class a `status`. To retire a term, mark it `owl:deprecated`; never delete it.
4. Save. If Protégé asks for a format, choose **RDF/XML Syntax**: the scripts
   can't read OWL/XML or Functional Syntax.
5. Run the quality checks (section 2) and fix what they report.
6. Update `scripts/next_id.txt` (see [Identifiers](#identifiers)).
7. Add a line under *Unreleased* in `CHANGELOG.md`.
8. Commit and push.

---

## 2. Quality checks

Run both after every change:

```
python scripts/find_problematic_terms.py nuclex-source.owl
python scripts/check_ids.py nuclex-source.owl
```

| Check | Script | Blocks release? |
|---|---|---|
| Approved term under an unapproved parent | `find_problematic_terms` | **Yes** |
| Missing, invalid, or multiple `status` | `find_problematic_terms` | **Yes** |
| Approved term with no definition | `find_problematic_terms` | Should be fixed |
| Approved term with no synonym | `find_problematic_terms` | No (advisory) |
| Duplicate labels, malformed IRIs, `next_id.txt` behind | `check_ids` | **Yes** |

`find_problematic_terms.py` writes its findings to `nuclex_qc_*.tsv`, which are not
committed. The `radiopharmaceutical compound` branch is skipped for the definition
and synonym checks; add `--check-all-branches` to include it.

---

## 3. Publishing a release

`X.Y.Z` is the new version and `P.Q.R` the previous one. Choose the number by
policy §11.1.

1. **Sync radiopharmaceuticals with NCIt** (policy §10.1):
   ```
   python scripts/sync_ncit.py nuclex-source.owl --dry-run
   python scripts/sync_ncit.py nuclex-source.owl --out nuclex-source-ncit.owl
   ```
   This writes a report, `ncit_sync_report.tsv`, and a new ontology,
   `nuclex-source-ncit.owl`. Read the report, then make the new ontology the
   working file (see [Applying a script's output](#applying-a-scripts-output)).
   Then deal with what the report flags:
   - *retired*: mark the term `owl:deprecated` in Protégé.
   - an unwanted *added* term: delete it in Protégé, and add its code to
     `scripts/ncit_skip.txt` so it doesn't return.
   - *added* terms go under their NCIt parent only. Also put them under any
     NucLex grouping class that fits (e.g. a PSMA-targeted group).
   - *relabelled*: the label now matches NCIt; the old label became a synonym.
     If you rename a term on purpose (e.g. EANM), list its NCIt code in
     `scripts/ncit_keep_labels.txt` so the next sync doesn't undo it.
2. **Check:** run both QC scripts on `nuclex-source.owl`. Everything that blocks
   a release must be 0.
3. **Update the header** in Protégé (*Active ontology* tab):
   `owl:versionIRI` → `https://nuclex.com/releases/X.Y.Z/nuclex.owl`,
   `owl:versionInfo` → `X.Y.Z`, `dcterms:modified` → today. Save.
4. **Preview:**
   ```
   python scripts/build_release.py nuclex-source.owl --only-approved --dry-run
   ```
   *Classes with no parent* should list only the real top-level classes.
5. **Build:**
   ```
   python scripts/build_release.py nuclex-source.owl --only-approved --out nuclex.owl
   ```
   Removes unapproved classes and strips `status`, `approver id`, `assigned to`.
6. **Compare with the previous release:**
   ```
   python scripts/check_ids.py nuclex.owl --previous releases/P.Q.R/nuclex.owl
   ```
   No identifier may vanish. Review every changed label.
7. **Freeze a copy with its QC record:**
   ```
   mkdir releases/X.Y.Z
   cp nuclex.owl releases/X.Y.Z/nuclex.owl
   python scripts/find_problematic_terms.py nuclex-source.owl --out-prefix releases/X.Y.Z/qc > releases/X.Y.Z/qc-report.txt
   ```
8. **Changelog:** rename *Unreleased* to `[X.Y.Z] — YYYY-MM-DD`; add a new empty
   *Unreleased* above it.
9. **Commit, tag, push:**
   ```
   git add -A && git commit -m "Release X.Y.Z"
   git tag vX.Y.Z && git push && git push --tags
   ```
10. Publish the files at their `https://nuclex.com/` addresses.

---

## Reference

### Files

| File | What it is |
|---|---|
| `nuclex-source.owl` | Working ontology: all terms plus curation metadata. Edited in Protégé. |
| `nuclex.owl` | Current release. Generated; never edited. |
| `releases/X.Y.Z/` | Frozen release copies and their QC record. Never edited. |
| `scripts/next_id.txt` | The next unused identifier for classes made in Protégé (range 1–19,999). |
| `scripts/next_import_id.txt` | The next unused identifier for imported classes (20,000–79,999). Updated by the sync scripts. |
| `scripts/ncit_skip.txt`, `nucleon_skip.txt` | Rejected NCIt / NUCLEON terms the syncs must not re-add. |
| `scripts/ncit_keep_labels.txt` | NCIt terms whose NucLex label is deliberate; the sync won't relabel them. |
| `contributions/incoming/`, `merged/` | Spreadsheets waiting to be integrated, and already integrated. |
| `deprecated/` | Retired code. **Never run `remint_DO_NOT_RUN_AGAIN.py`.** |

### Setup

Python 3 with `rdflib` (`pip install rdflib`). On Windows, set `PYTHONUTF8=1`
system-wide: labels contain Greek characters that otherwise crash the scripts.

#### Protégé setup

Set this before creating any class. A wrong setting once produced 60 bad IRIs.
*File → Preferences → New Entities*:

- IRI: specified IRI `https://nuclex.com/id/`, ending with an auto-generated ID
- Auto-generated ID: numeric, prefix `NUCLEX_`, 7 digits
- Start: the number in `scripts/next_id.txt`; remember last ID between sessions
- Label: the name you type becomes the `rdfs:label`

The counter is stored on your computer, not in the file. Recheck it on any new
machine.

### Identifiers

Numbers are never reused, even for a class deleted a minute after creation. Gaps
are permanent.

After each editing session, `check_ids.py` reports the next free identifier and
fails if `next_id.txt` is behind. Set `next_id.txt` to the higher of that value and
Protégé's next number (Protégé's is higher if you created then deleted classes).

Imported terms (sync scripts) use their own range, 20,000–79,999, and their own
counter, `next_import_id.txt`, which the scripts update themselves. Never set
Protégé's counter into that range.

A second curator gets their own number range (policy §3.3), not a shared counter.

### Adding definitions in bulk

`nuclex_qc_missing_definition.tsv` and `nuclex_qc_missing_synonym.tsv` are
worksheets: fill in `proposed_definition` and `proposed_new_synonyms` (several
synonyms separated by `;`), keep the file tab-separated, then:

```
python scripts/insert_definitions.py nuclex-source.owl contributions/incoming/FILE.tsv --dry-run
python scripts/insert_definitions.py nuclex-source.owl contributions/incoming/FILE.tsv --out nuclex-source-new.owl
```

Existing definitions are never overwritten (unless `--force`); rows whose label no
longer matches are skipped. Make `nuclex-source-new.owl` the working file (see
[Applying a script's output](#applying-a-scripts-output)), then move the worksheet
to `contributions/merged/` with a date prefix.

### Radionuclides from NUCLEON (occasional)

Not part of every release. Run it when NUCLEON publishes a new version (e.g. DICOM
adds nuclides to its lists), or after adding a radionuclide by hand so it gets its
`nucleon_id`:

```
python scripts/sync_nucleon.py nuclex-source.owl --dry-run
python scripts/sync_nucleon.py nuclex-source.owl --out nuclex-source-nucleon.owl
```

It adds `nucleon_id` to existing radionuclides that lack one, and adds any
DICOM-coded radionuclide NucLex doesn't have yet (policy §10.2). It writes a
report, `nucleon_sync_report.tsv`, and a new ontology, `nuclex-source-nucleon.owl`.
Read the report, then make the new ontology the working file (see
[Applying a script's output](#applying-a-scripts-output)). Running it when nothing
has changed does nothing.

### Applying a script's output

Scripts that change the ontology never overwrite `nuclex-source.owl`. They write a
new `.owl` file (e.g. `nuclex-source-ncit.owl`) next to it, plus a `.tsv` report
for you to read. To accept the changes:

1. Open the new `.owl` file in Protégé and spot-check the new or changed terms.
2. *File → Save as…*, choose format **RDF/XML Syntax**, choose `nuclex-source.owl`,
   and confirm replacing it.
   (Saving through Protégé, rather than copying the file, keeps Protégé's file
   layout so the git diff stays readable.)
3. Delete the new `.owl` file. It is not committed.

To reject the changes, just delete the new `.owl` file.

### Requests and approval

Term requests and feedback arrive through the two GitHub issue forms, labelled
`new term` or `term feedback` automatically. Add `accepted` or `declined` after
review, and put accepted issues in the milestone for their release. New and
modified terms need agreement from 3 of 4 subject matter experts.

### Scripts

| Script | Does |
|---|---|
| `find_problematic_terms.py` | QC checks; writes report TSVs |
| `check_ids.py` | Identifier checks; compares against a previous release |
| `build_release.py` | Builds the release from the source, to a new file |
| `insert_definitions.py` | Adds definitions and synonyms from a worksheet, to a new file |
| `sync_ncit.py` | Adds new NCIt radiopharmaceuticals; reports retired and renamed ones |
| `sync_nucleon.py` | Maps radionuclides to NUCLEON (`nucleon_id`); adds DICOM-coded radionuclides |
| `nxlib.py` | Shared code for the sync scripts (not run directly) |

No script overwrites the file it reads.
