# PSGC diff: 2025-3q → 2025-4q

From PSA's 2025-3q publication (as of 2025-09-30) to 2025-4q (as of 2025-12-31, [announcement](https://psa.gov.ph/classification/psgc/node/1684082306)). Claims are the rows of 2025-4q's Summary of Changes ('October to December 2025'), checked against both datafiles.

Written by `python scripts/psgc_data.py diff 2025-3q 2025-4q` from the committed files under `data/psgc/`; rerunning it gives this file unchanged.

2025-3q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

2025-4q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

## Summary

| | Count |
|---|---|
| Claims inconsistent | 0 |
| Claims not found | 0 |
| Claims unchecked | 0 |
| Claims consistent (spelling differs) | 0 |
| Claims consistent | 3 |
| Differences no claim explains | 0 |
| Summary count findings | 0 |
| Codes listed more than once | 0 |

## Claims: consistent (3)

| Status | Type | Claim | New code | Old name | Old code | Level | What the data shows |
|---|---|---|---|---|---|---|---|
| consistent | Correction of name | Barangay Villa Floresta, San Jose City, Nueva Ecija | 0304926040 | Villa Floresca | 0304926040 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, Municipality of Magallanes, Agusan del Norte | 1600208010 | Santo Niño | 1600208010 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Rosario, Municipality of Magallanes, Agusan del Norte | 1600208011 | Santo Rosario | 1600208011 | Bgy |  |

## Differences no claim explains (0)

None: every difference between the two datafiles is covered by a claim.

## Summary counts against the PSGC sheet (0)

Every region's province, city, municipality and barangay count in both national summaries matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code).
