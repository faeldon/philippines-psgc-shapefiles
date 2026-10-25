# PSGC diff: 2026-1q → 2026-2q

From PSA's 2026-1q publication (as of 2026-03-31) to 2026-2q (as of 2026-06-30, [announcement](https://psa.gov.ph/classification/psgc/node/1684083815)). Claims are the rows of 2026-2q's Summary of Changes ('April to June 2026'), checked against both datafiles.

Written by `python scripts/psgc_data.py diff 2026-1q 2026-2q` from the committed files under `data/psgc/`; rerunning it gives this file unchanged.

2026-1q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

2026-2q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

## Summary

| | Count |
|---|---|
| Claims inconsistent | 0 |
| Claims not found | 0 |
| Claims unchecked | 0 |
| Claims consistent (spelling differs) | 0 |
| Claims consistent | 17 |
| Differences no claim explains | 0 |
| Summary count findings | 0 |
| Codes listed more than once | 0 |

## Claims: consistent (17)

| Status | Type | Claim | New code | Old name | Old code | Level | What the data shows |
|---|---|---|---|---|---|---|---|
| consistent | Change of name | Municipality of Sawata, Davao del Norte | 1102324000 | San Isidro | 1102324000 | Mun |  |
| consistent | Change of name | Barangay Poblacion, Sawata, Davao del Norte | 1102324013 | Sawata | 1102324013 | Bgy |  |
| consistent | Correction of name | Municipality of Don Victoriano, Misamis Occidental | 1004217000 | Don Victoriano Chiongbian | 1004217000 | Mun |  |
| consistent | Correction of name | Barangay Parang-Parang, Orani, Bataan | 0300809015 | Parang Parang | 0300809015 | Bgy |  |
| consistent | Correction of name | Barangay Barorawon, Kalilangan, Bukidnon | 1001307002 | Baborawon | 1001307002 | Bgy |  |
| consistent | Correction of name | Barangay Macaopao, Kalilangan, Bukidnon | 1001307007 | Maca-opao | 1001307007 | Bgy |  |
| consistent | Correction of name | Barangay Balocbocan, Kitaotao, Bukidnon | 1001309002 | Balukbukan | 1001309002 | Bgy |  |
| consistent | Correction of name | Barangay Indalasa, City of Malaybalay, Bukidnon | 1001312018 | Indalaza | 1001312018 | Bgy |  |
| consistent | Correction of name | Barangay Kibalabag, City of Malaybalay, Bukidnon | 1001312021 | Kabalabag | 1001312021 | Bgy |  |
| consistent | Correction of name | Barangay Merangeran, Quezon, Bukidnon | 1001317019 | Merangerang | 1001317019 | Bgy |  |
| consistent | Correction of name | Barangay Sta. Cruz, Quezon, Bukidnon | 1001317034 | Santa Cruz | 1001317034 | Bgy |  |
| consistent | Correction of name | Barangay Kulasi, Sumilao, Bukidnon | 1001319002 | Culasi | 1001319002 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, Talakag, Bukidnon | 1001320016 | Santo Niño | 1001320016 | Bgy |  |
| consistent | Correction of name | Barangay Nabag-o, City of Valencia, Bukidnon | 1001321022 | Nabago | 1001321022 | Bgy |  |
| consistent | Correction of name | Barangay Kahaponan, City of Valencia, Bukidnon | 1001321011 | Kahapunan | 1001321011 | Bgy |  |
| consistent | Correction of name | Barangay Lurugan, City of Valencia, Bukidnon | 1001321017 | Lurogan | 1001321017 | Bgy |  |
| consistent | Correction of name | Barangay Sta. Ines, Malitbog, Bukidnon | 1001313009 | Santa Ines | 1001313009 | Bgy |  |

## Differences no claim explains (0)

None: every difference between the two datafiles is covered by a claim.

## Summary counts against the PSGC sheet (0)

Every region's province, city, municipality and barangay count in both national summaries matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code).
