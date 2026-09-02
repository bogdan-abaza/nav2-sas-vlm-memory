# Known discrepancies in the Session E source documents

Every item below is a conflict **between source documents**, carried into this dataset
unresolved on purpose. Nothing was edited to make the sources agree. Each item states
which value the audit logs support, and shows the arithmetic so the reader can check it.

## D-1 · A superseded copy of the day-2 session notes

The delivered archive contains **one** day-2 note, at `notes/`. The working folder on
the author machine contained a second copy at `ziua2_20260821/`, same byte length, with
**one differing line**:

* delivered  (`notes/session_notes_day2_20260821_ro.md`): *"10 esecuri din 63 de apeluri L3b, 15.9%"*
* not delivered (`_outside_delivery/session_notes_day2_ro_superseded_draft.md`): *"... din 51 ... 19.6%"*

The delivered figure is the correct one. From `missions.csv`, day 2:

```
resolution_method == "L3b_vlm"      53   L3b calls that returned parseable JSON
resolution_method == "escalated"    10   L3b calls that did not
                                  ----
total L3b calls                     63   failure rate 10/63 = 15.9%
```

The denominator 51 cannot be reconstructed from any field in the logs. The draft is
kept under `_outside_delivery/` so the discrepancy stays auditable, but it carries no
evidential weight: it was never part of the delivery.

## D-2 · Three different denominators for the L3b failure rate

The source documents use three incompatible conventions. They differ in whether
negation-blocked calls count as L3b calls:

| document | day | quoted | denominator is |
|---|---|---|---|
| `_source/MANIFEST_ro.txt` | 1 | 4 / 42 = 9.5% | `L3b_vlm` + `L3b_vlm_negation_blocked` + `escalated` = 16 + 22 + 4 |
| session notes | 1 | 4 / 20 = 20% | `L3b_vlm` + `escalated` = 16 + 4 |
| session notes rev B | 2 | 10 / 63 = 15.9% | `L3b_vlm` + `escalated` = 53 + 10 |
| session notes rev A | 2 | 10 / 51 = 19.6% | not reconstructible |

Day 2 has **zero** `L3b_vlm_negation_blocked` records (0), so on day 2 the first
two conventions coincide. On day 1 they do not, which is why the same day is reported
both as 9.5% and as 20%.

**Recommended convention for the paper**, applied identically to both days:
`L3b_vlm + escalated`, i.e. calls that were issued and either parsed or did not.
A negation-blocked call is a guard decision, not an L3b outcome. Under that convention:

```
day 1  4 / 20 = 20.0%
day 2  10 / 63 = 15.9%
```

Whichever convention is chosen, it must be stated and used for both days.

## D-3 · Record count vs decision count

`_source/MANIFEST_ro.txt` reports 89 and 123 "linii de decizie". `missions.csv` has
93 and 133 rows. The difference is exactly the `escalated` records
(4 and 10), which the manifest excludes:

```
day1_20260820: 93 rows - 4 escalated = 89 decision lines
day2_20260821: 133 rows - 10 escalated = 123 decision lines
```

Filter `is_escalated = "no"` in `missions.csv` to reproduce the manifest figure.

## D-4 · Superseded `content_md5` in the day-1 configuration

`day1_20260820/config/digest_hashes.txt` records
`content_md5 = bdc89fcf1e17f8c577a941cd80be70ab`, labelled "cel din audit" ("the one from
the audit"). The label is wrong: the day-1 audits record
`digest_content_md5 = 0fd61f9e82e8fe6991f0311014384e0c` in every record. The error was
caught by the start-gate script on 21 August and corrected in
`day2_20260821/session/digest_hashes_corrected.txt`, which is the file to cite. The
original is kept because it is what the day-1 runs were configured against.

## D-5 · Images from aborted runs

3 images are present on disk but referenced by no audit record. They belong to
runs that were started and abandoned before a decision was written:

* `day1_20260820/logs/20260820_124642/mission_2_plant_5/start.jpg`
* `day2_20260821/logs/20260821_104307/mission_1_cb202/start.jpg`
* `day2_20260821/logs/20260821_113819/mission_1_toilet_m/start.jpg`

They are kept for completeness and should be excluded from any per-mission analysis;
`missions.csv` already excludes them, since it lists only images an audit record references.

## D-6 · AprilTag id1 — surveyed pose inconsistent with its optical geometry

Recorded here because it constrains what the external-localization analysis may use.
Across four arrivals near `plant_3`, on both days, tag id1 places the camera at
0.331 m +/- 0.012 m above the floor. The camera on `xplorer-c` is at 0.170 m, and the same
platform against tag id3 returns 0.126-0.171 m. No tag height or rotation about the
vertical closes the geometry; matching the camera height would require the tag centre at
-0.08 m, below the floor. The tag is therefore not mounted as surveyed, and its four
samples are excluded from the external-reference aggregate. See
`external_reference/README.md`.

