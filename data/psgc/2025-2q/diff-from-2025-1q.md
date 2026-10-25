# PSGC diff: 2025-1q → 2025-2q

From PSA's 2025-1q publication (as of 2025-03-31) to 2025-2q (as of 2025-06-30, [announcement](https://psa.gov.ph/classification/psgc/node/1684077694)). Claims are the rows of 2025-2q's Summary of Changes ('April to June 2025'), checked against both datafiles.

Written by `python scripts/psgc_data.py diff 2025-1q 2025-2q` from the committed files under `data/psgc/`; rerunning it gives this file unchanged.

2025-1q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

2025-2q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

## Summary

| | Count |
|---|---|
| Claims inconsistent | 0 |
| Claims not found | 0 |
| Claims unchecked | 0 |
| Claims consistent (spelling differs) | 0 |
| Claims consistent | 3 |
| Differences no claim explains | 19 |
| Summary count findings | 0 |
| Codes listed more than once | 0 |

## Claims: consistent (3)

| Status | Type | Claim | New code | Old name | Old code | Level | What the data shows |
|---|---|---|---|---|---|---|---|
| consistent | Correction of name | Barangay Sto. Niño, Araceli, Palawan | 1705303011 | Santo Niño | 1705303011 | Bgy |  |
| consistent | Correction of name | Barangay Mangingisda, City of Puerto Princesa | 1731500062 | Barangay ng mga Mangingisda | 1731500062 | Bgy |  |
| consistent | Correction of name | Barangay Sta. Maria, Abra De Ilog, Occidental Mindoro | 1705101010 | Santa Maria | 1705101010 | Bgy |  |

## Differences no claim explains (19)

| Change | Code | Name in 2025-1q | Name in 2025-2q | Level | Level after | Detail |
|---|---|---|---|---|---|---|
| changed | 0405622058 | Rizal | Rizal (Rural) | Bgy | Bgy | renamed |
| changed | 0405622095 | Rizal | Rizal (Poblacion) | Bgy | Bgy | renamed |
| changed | 0506213047 | San Antonio | San Antonio (Millabas) | Bgy | Bgy | renamed |
| changed | 0506213048 | San Antonio | San Antonio (Sapa) | Bgy | Bgy | renamed |
| changed | 0506216003 | Balogo | Balogo (Sorsogon East District) | Bgy | Bgy | renamed |
| changed | 0506216010 | Buenavista | Buenavista (Sorsogon West District) | Bgy | Bgy | renamed |
| changed | 0506216029 | Salvacion | Salvacion (Sorsogon West District) | Bgy | Bgy | renamed |
| changed | 0506216031 | San Isidro | San Isidro (Sorsogon West District) | Bgy | Bgy | renamed |
| changed | 0506216032 | San Juan | San Juan (Roro) | Bgy | Bgy | renamed |
| changed | 0506216039 | Balogo | Balogo (Bacon District) | Bgy | Bgy | renamed |
| changed | 0506216043 | Buenavista | Buenavista (Bacon District) | Bgy | Bgy | renamed |
| changed | 0506216053 | Salvacion | Salvacion (Bacon District) | Bgy | Bgy | renamed |
| changed | 0506216054 | San Isidro | San Isidro (Bacon District) | Bgy | Bgy | renamed |
| changed | 0931700027 | Dulian | Dulian (Upper Bunguiao) | Bgy | Bgy | renamed |
| changed | 0931700028 | Dulian | Dulian (Upper Pasonanca) | Bgy | Bgy | renamed |
| changed | 1102317012 | Cogon | Cogon (Talicod) | Bgy | Bgy | renamed |
| changed | 1102317032 | San Isidro | San Isidro (Babak) | Bgy | Bgy | renamed |
| changed | 1102317033 | San Isidro | San Isidro (Kaputian) | Bgy | Bgy | renamed |
| changed | 1908821013 | Pagatin | Pagatin (Pagatin I) | Bgy | Bgy | renamed |

## Summary counts against the PSGC sheet (0)

Every region's province, city, municipality and barangay count in both national summaries matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code).
