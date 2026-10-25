# PSGC diff: 2024-4q → 2025-1q

From PSA's 2024-4q publication (as of 2024-12-31) to 2025-1q (as of 2025-03-31, [announcement](https://psa.gov.ph/classification/psgc/node/1684076101)). Claims are the rows of 2025-1q's Summary of Changes ('January to March 2025'), checked against both datafiles.

Written by `python scripts/psgc_data.py diff 2024-4q 2025-1q` from the committed files under `data/psgc/`; rerunning it gives this file unchanged.

2024-4q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

2025-1q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

## Summary

| | Count |
|---|---|
| Claims inconsistent | 0 |
| Claims not found | 0 |
| Claims unchecked | 0 |
| Claims consistent (spelling differs) | 0 |
| Claims consistent | 7 |
| Differences no claim explains | 0 |
| Summary count findings | 0 |
| Codes listed more than once | 0 |

## Claims: consistent (7)

| Status | Type | Claim | New code | Old name | Old code | Level | What the data shows |
|---|---|---|---|---|---|---|---|
| consistent | Correction of name | Municipality of Dr. Jose P. Rizal, Palawan | 1705323000 | Rizal | 1705323000 | Mun |  |
| consistent | Correction of name | Barangay Carabao, Culion, Palawan | 1705322014 | De Carabao | 1705322014 | Bgy |  |
| consistent | Correction of name | Barangay Concepcion 1, Municipality of Sariaya, Quezon | 0405645013 | Concepcion No. 1 | 0405645013 | Bgy |  |
| consistent | Correction of name | Barangay Guisguis San Roque, Municipality of Sariaya, Quezon | 0405645016 | Guisguis-San Roque | 0405645016 | Bgy |  |
| consistent | Correction of name | Barangay Guisguis Talon, Municipality of Sariaya, Quezon | 0405645017 | Guisguis-Talon | 0405645017 | Bgy |  |
| consistent | Correction of name | Barangay Sta. Lucia, Sablayan, Occidental Mindoro | 1705109018 | Santa Lucia | 1705109018 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, Sablayan, Occidental Mindoro | 1705109019 | Santo Niño | 1705109019 | Bgy |  |

## Differences no claim explains (0)

None: every difference between the two datafiles is covered by a claim.

## Summary counts against the PSGC sheet (0)

Every region's province, city, municipality and barangay count in both national summaries matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code).
