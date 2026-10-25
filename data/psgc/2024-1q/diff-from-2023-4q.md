# PSGC diff: 2023-4q → 2024-1q

From PSA's 2023-4q publication (as of 2023-12-31) to 2024-1q (as of 2024-03-31, [announcement](https://psa.gov.ph/classification/psgc/node/1684063392)). Claims are the rows of 2024-1q's Summary of Changes ('January to March 2024'), checked against both datafiles.

Written by `python scripts/psgc_data.py diff 2023-4q 2024-1q` from the committed files under `data/psgc/`; rerunning it gives this file unchanged.

2024-1q's datafile lacks 4 rows its manifest adds (1303900000, 1307400000, 1307500000, 1307600000); differences in them are the manifest's, not PSA's, and aren't listed below.

## Summary

| | Count |
|---|---|
| Claims inconsistent | 0 |
| Claims not found | 0 |
| Claims unchecked | 0 |
| Claims consistent (spelling differs) | 0 |
| Claims consistent | 24 |
| Differences no claim explains | 1 |
| Summary count findings | 0 |
| Codes listed more than once | 0 |

## Claims: consistent (24)

| Status | Type | Claim | New code | Old name | Old code | Level | What the data shows |
|---|---|---|---|---|---|---|---|
| consistent | Newly created barangay | Barangay Sultan Corobong, City of Marawi, Lanao del Sur | 1903617147 | Dulay | 1903617040 | Bgy |  |
| consistent | Newly created barangay | Barangay Sultan Panoroganan, City of Marawi, Lanao del Sur | 1903617148 | Kilala | 1903617052 | Bgy |  |
| consistent | Newly created barangay | Barangay Angoyao, City of Marawi, Lanao del Sur | 1903617146 | Patani | 1903617099 | Bgy |  |
| consistent | Transfer of barangay | Barangay Guintolan, Imelda, Zamboanga Sibugay | 0908304019 | Guintolan, Payao, Zamboanga Sibugay | 0908311008 | Bgy |  |
| consistent | Correction of name | Barangay Hibunawan, Municipality of Burauen, Leyte | 0803710032 | Hibonawan | 0803710032 | Bgy |  |
| consistent | Correction of name | Barangay Gitabla, Municipality of Burauen, Leyte | 0803710030 | Gitablan | 0803710030 | Bgy |  |
| consistent | Correction of name | Barangay Digahungan, Municipality of Dagami, Leyte | 0803717021 | Digahongan | 0803717021 | Bgy |  |
| consistent | Correction of name | Barangay Hitomnog, Municipality of Dagami, Leyte | 0803717027 | Hitumnog | 0803717027 | Bgy |  |
| consistent | Correction of name | Barangay Lapu-Lapu, Municipality of Dagami, Leyte | 0803717040 | Lapu-lapu Pob. | 0803717040 | Bgy |  |
| consistent | Correction of name | Barangay Lobe-Lobe, Municipality of Dagami, Leyte | 0803717030 | Lobe-lobe | 0803717030 | Bgy |  |
| consistent | Correction of name | Barangay Lobe-Lobe East, Municipality of Dagami, Leyte | 0803717060 | Lobe-lobe East | 0803717060 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Domingo, Municipality of Dagami, Leyte | 0803717052 | Santo Domingo | 0803717052 | Bgy |  |
| consistent | Correction of name | Barangay Casulongan, Municipality of Javier, Leyte | 0803724009 | Casalungan | 0803724009 | Bgy |  |
| consistent | Correction of name | Barangay Sta. Cruz, Municipality of Julita, Leyte | 0803725024 | Santa Cruz | 0803725024 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, Municipality of Julita, Leyte | 0803725025 | Santo Niño | 0803725025 | Bgy |  |
| consistent | Correction of name | Barangay Gimiranat East, Municipality of La Paz, Leyte | 0803728015 | Gimenarat East | 0803728015 | Bgy |  |
| consistent | Correction of name | Barangay Gimiranat West, Municipality of La Paz, Leyte | 0803728016 | Gimenarat West | 0803728016 | Bgy |  |
| consistent | Correction of name | Barangay Palanogan, Municipality of Mahaplag, Leyte | 0803731014 | Palañogan | 0803731014 | Bgy |  |
| consistent | Correction of name | Barangay Sta. Cruz, Municipality of Mahaplag, Leyte | 0803731021 | Santa Cruz | 0803731021 | Bgy |  |
| consistent | Correction of name | Barangay Sto. Niño, Municipality of Mahaplag, Leyte | 0803731028 | Santo Niño | 0803731028 | Bgy |  |
| consistent | Correction of name | Barangay Mercaduhay, Municipality of Tabontabon, Leyte | 0803746009 | Mercadohay | 0803746009 | Bgy |  |
| consistent | Correction of name | Barangay Guingauan, Municipality of Tabontabon, Leyte | 0803746007 | Guingawan | 0803746007 | Bgy |  |
| consistent | Correction of name | Barangay Apurawan, Municipality of Aborlan, Palawan | 1705301003 | Aporawan | 1705301003 | Bgy |  |
| consistent | Correction of name | Barangay Apoaporawan, Municipality of Aborlan, Palawan | 1705301001 | Apo-Aporawan | 1705301001 | Bgy |  |

## Differences no claim explains (1)

| Change | Code | Name in 2023-4q | Name in 2024-1q | Level | Level after | Detail |
|---|---|---|---|---|---|---|
| changed | 1705306000 | Brooke'S Point | Brooke's Point | Mun | Mun | renamed |

## Summary counts against the PSGC sheet (0)

Every region's province, city, municipality and barangay count in both national summaries matches its PSGC sheet (Prov, City, Mun and Bgy rows by region code).
