# PSGC diff: 2024-2q → 2024-3q

From PSA's 2024-2q publication (as of 2024-06-30) to 2024-3q (as of 2024-09-30, [announcement](https://psa.gov.ph/classification/psgc/node/1684065214)). Claims are the rows of 2024-3q's Summary of Changes ('July to September 2024'), checked against both datafiles.

Written by `python scripts/psgc_data.py diff 2024-2q 2024-3q` from the committed files under `data/psgc/`; rerunning it gives this file unchanged.

2024-2q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

2024-3q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

## Summary

| | Count |
|---|---|
| Claims inconsistent | 0 |
| Claims not found | 0 |
| Claims unchecked | 0 |
| Claims consistent (spelling differs) | 0 |
| Claims consistent | 12 |
| Differences no claim explains | 0 |
| Summary count findings | 0 |
| Codes listed more than once | 0 |

## Claims: consistent (12)

| Status | Type | Claim | New code | Old name | Old code | Level | What the data shows |
|---|---|---|---|---|---|---|---|
| consistent | Newly created barangay | Barangay Juan-Loreto Tamayo, Municipality of Tupi, South Cotabato | 1206317017 | Cebuano | 1206317004 | Bgy |  |
| consistent | Newly created barangay | Barangay Guinhalinan, Municipality of Barobo, Surigao del Sur | 1606801027 | Javier | 1606801010 | Bgy |  |
| consistent | Division of barangay | Barangay 176-A, City of Caloocan | 1380100189 | Barangay 176, City of Caloocan | 1380100176 | Bgy |  |
| consistent | Division of barangay | Barangay 176-B, City of Caloocan | 1380100190 |  |  | Bgy |  |
| consistent | Division of barangay | Barangay 176-C, City of Caloocan | 1380100191 |  |  | Bgy |  |
| consistent | Division of barangay | Barangay 176-D, City of Caloocan | 1380100192 |  |  | Bgy |  |
| consistent | Division of barangay | Barangay 176-E, City of Caloocan | 1380100193 |  |  | Bgy |  |
| consistent | Division of barangay | Barangay 176-F, City of Caloocan | 1380100194 |  |  | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, Municipality of Carmen, Davao del Norte | 1102303019 | Santo Niño | 1102303019 | Bgy |  |
| consistent | Correction of name | Barangay Sta. Cruz, Municipality of New Corella, Davao del Norte | 1102314016 | Santa Cruz | 1102314016 | Bgy |  |
| consistent | Correction of name | Barangay Sta. Fe, Municipality of New Corella, Davao del Norte | 1102314017 | Santa Fe | 1102314017 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, Municipality of New Corella, Davao del Norte | 1102314018 | Santo Niño | 1102314018 | Bgy |  |

## Differences no claim explains (0)

None: every difference between the two datafiles is covered by a claim.

## Summary counts against the PSGC sheet (0)

Every region's province, city, municipality and barangay count in both national summaries matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code).
