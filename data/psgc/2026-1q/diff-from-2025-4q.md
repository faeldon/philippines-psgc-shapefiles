# PSGC diff: 2025-4q → 2026-1q

From PSA's 2025-4q publication (as of 2025-12-31) to 2026-1q (as of 2026-03-31, [announcement](https://psa.gov.ph/classification/psgc/node/1684083211)). Claims are the rows of 2026-1q's Summary of Changes ('January to March 2026'), checked against both datafiles.

Written by `python scripts/psgc_data.py diff 2025-4q 2026-1q` from the committed files under `data/psgc/`; rerunning it gives this file unchanged.

2025-4q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

2026-1q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

## Summary

| | Count |
|---|---|
| Claims inconsistent | 0 |
| Claims not found | 0 |
| Claims unchecked | 0 |
| Claims consistent (spelling differs) | 0 |
| Claims consistent | 9 |
| Differences no claim explains | 0 |
| Summary count findings | 0 |
| Codes listed more than once | 0 |

## Claims: consistent (9)

| Status | Type | Claim | New code | Old name | Old code | Level | What the data shows |
|---|---|---|---|---|---|---|---|
| consistent | Merging of barangays | Barangay Dacanlao, City of Calaca, Batangas | 0401007019 | Dacanlao | 0401007019 | Bgy |  |
| consistent | Correction of name | Municipality of Sanchez Mira, Cagayan | 0201522000 | Sanchez-Mira | 0201522000 | Mun |  |
| consistent | Correction of name | Barangay Genitligan, Municipality of Baras, Catanduanes | 0502002010 | Ginitligan | 0502002010 | Bgy |  |
| consistent | Correction of name | Barangay Ambuklao, Municipality of Bokod, Benguet | 1401104001 | Ambuclao | 1401104001 | Bgy |  |
| consistent | Correction of name | Barangay Daklan, Municipality of Bokod, Benguet | 1401104004 | Daclan | 1401104004 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Rosario, Municipality of Kitaotao, Bukidnon | 1001309030 | Santo Rosario | 1001309030 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, Manolo Fortich, Bukidnon | 1001314021 | Santo Niño | 1001314021 | Bgy |  |
| consistent | Correction of name | Barangay St. Peter, City of Malaybalay, Bukidnon | 1001312058 | Saint Peter | 1001312058 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, City of Malaybalay, Bukidnon | 1001312061 | Santo Niño | 1001312061 | Bgy |  |

## Differences no claim explains (0)

None: every difference between the two datafiles is covered by a claim.

## Summary counts against the PSGC sheet (0)

Every region's province, city, municipality and barangay count in both national summaries matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code).
