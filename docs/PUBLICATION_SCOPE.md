# Publication scope and evidence policy

This document defines what this repository publishes, what it deliberately does not, and the
rules under which its contents may be read as evidence. It is the reader-facing declaration
of the publication policy; the release gate enforces that policy together with the
associated machine-readable exception and link-resolution registries, published under
`docs/`. The policies stated here were fixed before the release was assembled.

## 1. What is published, and what is not

The repository publishes the raw session evidence of the three April sessions and of Session E
(August 2026) byte-identically, including all 358 Session E images, without exception; the unified
session indexes; the supporting analyses for the revision; and one production source module,
`data/session_e/public_code/sas_text.py`, the text-normalisation layer of the SAS. It is the
only production module in the public package: the delivery code directories of the two
Session E days are replaced at the publication boundary by the `public_code` directory, and
the remaining production source is not published. The complete source remains available to
the editor and reviewers, in confidence, upon request through the journal.

## 2. Policy statement

The release was assembled under the following policy, fixed on 29 August 2026:

> Scope-aware publication gate with immutable frozen evidence, digest-bound enumerated
> exceptions, explicit source-bound supersession, repair-before-exception link handling,
> separate public-release provenance, and adversarial validation of the exception mechanism.

Its operative meaning for a reader: **frozen analytical prose is an immutable historical
record, while current scientific claims are governed by the revised manuscript and current
repository documentation.** The presence of a superseded formulation inside a frozen record
does not reactivate it as a current claim.

Superseded claims or terminology in current repository prose are hard release-gate
failures. They are admissible only when they occur inside a cryptographically identified
frozen record and are individually enumerated in `docs/publication_exceptions.json`. Any
byte-level modification of a frozen file invalidates its associated exceptions
automatically.

## 3. Frozen analytical records and superseded formulations

The frozen analytical records published under `analysis/session_e/`, including the core
point-by-point record `analysis/session_e/core/RESULTS_E.md` and the frozen supporting
analyses, are published exactly as sealed, with their identities attested by their
associated checksum manifests. Because these records answer the reviewers point by point,
they necessarily quote, name, and measure quantitative claims and terminology from the
original submission that the revision has since narrowed or retired. Such passages are
objects of analysis, not assertions of this release.

The current machine-readable Session E analysis used to govern quantitative supersession is
`analysis/session_e/core/results_E.json`, SHA-256
`12e9ff2e4b664baef2ee60206cb309b5458f2d11fed0f83ac9a73b69b08d430e`. It is a controlled
release analysis artifact and is outside the immutable-prose exception domain. Whenever a
superseded quantitative formulation occurs in a frozen record, its current interpretation
is linked through `docs/publication_exceptions.json` to the canonical machine-readable
source governing that claim. Each such source is identified explicitly by repository path
and SHA-256 digest; where a replacement value is quantitative, it is derived
programmatically from that source rather than manually re-entered.

Evidence identifiers A1, A2, A3 and R210-AN-02 name the frozen supporting analyses of this
revision and are used as public cross-references throughout the repository and the response
to reviewers. These identifiers are public evidence identifiers for the repository and the
response-to-reviewers evidence chain; this does not make them manuscript terminology.
Internal governance identifiers such as `T-VERSION` are not public evidence identifiers
and, where preserved inside a frozen record, are handled only through individually
enumerated digest-bound exceptions.

## 4. Exception and supersession registries

The finite exception registry is stored in `docs/publication_exceptions.json`. Each
exception identifies the frozen file, its SHA-256 digest, the authorized occurrence and its
classification; supersession entries also identify the governing source by path and digest.
Supersession takes one of three declared forms: a numeric interpretation derived from a
machine-readable source, an evidentiary-scope interpretation, or a terminology
interpretation. Link relocations and deliberate publication-boundary exclusions are
recorded separately in `docs/link_resolution_map.json`. These registries do not relax the
current-prose rules; beyond one declared use–mention of a governance identifier in this
policy document, they only account for explicitly identified content in immutable
historical records.

## 5. Link resolution and publication-boundary references

Relative references in current repository documentation must resolve within the public
release and are repaired rather than excepted whenever a public target exists. For frozen
records, `docs/link_resolution_map.json` records the verified public target where one
exists. An enumerated link exception is permitted only when the historical target is
deliberately outside the publication boundary or has been superseded; exceptions are not
used in place of a resolvable public target.

## 6. Network addresses and machine paths in the raw evidence

237 published files — Session E raw records and supporting-analysis input tables — carry
deployment-local identifiers preserved for provenance: the private LAN addresses
192.168.53.60 and 192.168.53.159 (232 files) and/or the workstation path /home/fiir-eq2
(233 files). Both addresses are RFC 1918 private-range addresses, reachable only inside the
experimental network, which no longer exists in that configuration; the path names a local
account on the robot workstation. Neither constitutes a publicly routable
endpoint or a credential, and neither is required as a live location to reproduce the
published analyses. They are
published byte-identically, by an explicit decision of 28 August 2026: these values appear
inside sealed, checksummed evidence whose verifiability rests on byte-identity, so redacting
them would break every downstream digest without changing the public attack
surface. The same account path already appears in the raw logs of the April
sessions published since May.

## 7. Integrity and provenance

`data/session_e/CHECKSUMS_PUBLIC.md5` is the checksum manifest of the published Session E
package, generated over exactly the files present here. The delivery-time checksum manifest
is not published, because it also covers delivered files that are outside the publication
boundary; it remains part of the sealed delivery. `data/session_e/PROVENANCE.tsv` is the
delivered provenance record and is published unmodified; it is never extended or edited
retrospectively. Files added to the public package after delivery — the external
localization reference under `data/session_e/external_reference/` — are recorded separately
in `data/session_e/PROVENANCE_PUBLIC.tsv`. The two frozen acquisition archives of the
model-substitution replay are likewise published byte-identically, inside
`analysis/session_e/r210_model_replay/`, after a full disclosure scan; their SHA-256
digests are carried by that package's own checksum manifest, and the reproduction notes in
`docs/REPRODUCIBILITY_NOTES.md` state exactly which frozen procedures are executable from
this release.

### Declared post-delivery difference

In two memory files of the Xplorer-B platform, the navigator version field reads `v4.8`
where the delivered evidence recorded `v4.7.4`. The discrepancy was found during release
preparation and is documented in `data/session_e/KNOWN_DISCREPANCIES.md`. The two released
M4 records therefore differ from their delivery-time counterparts only in this declared
field. M4 `navigator_version` is snapshot-level platform metadata and must not be used to
infer the software version of an A–C experimental run; run-level version provenance is
provided by `navigator_startup.version` in the corresponding audit records.

## 8. Language of the primary evidence

Primary evidence across the April sessions and Session E may contain Romanian-language
operator instructions, session notes, mission annotations, or other text recorded during
the experiments. These records are preserved in their original language and are not
translated in place, because a translation would replace part of the primary record with an
interpretation.

Current repository documentation and reader-facing indexes are written in English. Where
Romanian-language primary evidence is materially used to support a reported result,
English-language access is provided through the corresponding index, analysis, or an
explicitly labelled companion translation. Any such English rendering is interpretive and
non-authoritative; the original record remains the evidentiary source.

## 9. Peer-review traceability metadata

Identifiers of the form `R1-x` and `R2-x` that remain inside immutable analytical
artifacts are author-generated traceability labels used to organize the revision evidence.
They do not identify reviewers and do not reproduce reviewer reports or reviewer-authored
text. Manuscript tracking identifiers and reviewer-point labels are excluded from current
reader-facing repository prose unless required to explain the provenance of an immutable
frozen record. The author-side reviewer-to-evidence traceability matrix and response
correspondence remain outside the public repository.

The journal manuscript tracking identifier may occur in immutable deployment or analytical
records as historical provenance metadata. It is not used in current reader-facing
repository prose.

## 10. Validation status

The release gate was additionally tested against deliberately invalid conditions, including
a mismatched frozen-file digest, a newly introduced retired formulation in current prose,
and an occurrence beyond the authorized count; each condition was rejected.
