# PSGC diff: 2024-3q → 2024-4q

From PSA's 2024-3q publication (as of 2024-09-30) to 2024-4q (as of 2024-12-31, [announcement](https://psa.gov.ph/classification/psgc/node/1684066655)). Claims are the rows of 2024-4q's Summary of Changes ('October to December 2024'), checked against both datafiles.

Written by `python scripts/psgc_data.py diff 2024-3q 2024-4q` from the committed files under `data/psgc/`; rerunning it gives this file unchanged.

2024-3q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

2024-4q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

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
| consistent | Correction of name | Barangay Gaswiling, Municipality of Kapangan, Benguet | 1401108010 | Gasweling | 1401108010 | Bgy |  |
| consistent | Correction of name | Barangay Guevara, Municipality of La Paz, Tarlac | 0306907007 | Guevarra | 0306907007 | Bgy |  |
| consistent | Correction of name | Barangay Anhawan, Municipality of Dauin, Negros Oriental | 1804609001 | Anahawan | 1804609001 | Bgy |  |

## Differences no claim explains (0)

None: every difference between the two datafiles is covered by a claim.

## Summary counts against the PSGC sheet (0)

Every region's province, city, municipality and barangay count in both national summaries matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code).
