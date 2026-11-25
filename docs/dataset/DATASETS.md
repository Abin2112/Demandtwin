# Data sources and access

The [dataset catalogue](../../data/metadata/dataset_catalogue.json) records source versions, access status and local observed metadata.

| Dataset | Evidence and access |
| --- | --- |
| UCI Online Retail | Downloaded CC BY 4.0 UK retailer transactions. Retained UK purchase lines are used for a 30-day repeat-invoice benchmark. Attribute to Daqing Chen (2015), DOI 10.24432/C5BW33. |
| India HCES 2022–23 and 2023–24 | Official questionnaires, variable dictionaries and public-use catalogue entries reviewed. The microdata download uses the MoSPI account workflow. Apply the survey weights and design documentation before reporting expenditure estimates. |
| Amazon Reviews 2023 grocery | The official catalogue identifies 7.0 million grocery reviews. Dataset redistribution rights were unconfirmed, so acquisition is deferred. Product and review representations are eligible research targets once rights are established. |
| Open Food Facts | ODbL product database. To run the bounded India snacks query, set `OFF_USER_AGENT` to include a project URL or contact and run `scripts/download_datasets.py off_india`. Follow attribution and share-alike requirements before distributing any derived database. The query excludes image downloads. |
| Twin-2K-500 | Official CC BY 4.0 US survey panel. Downloaded the question catalogue and two numeric response tables. The fidelity benchmark uses only repeated hypothetical pricing answers and writes aggregate metrics. |
| Other candidate sources | UCI Online Retail II overlaps the same UK retailer and period. The Zenodo fig-jam DCE is closer to the product category but has restricted files. Neither was included. |
| Synthetic choice panel | Generated locally. Every record carries a synthetic flag. Used to verify conditional choice modeling, adaptive design and the integrated app. |

[UCI record](https://doi.org/10.24432/C5BW33) · [HCES catalogue](https://microdata.gov.in/nada/index.php/catalog/CEXP) · [Amazon release](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023) · [Open Food Facts API terms](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/) · [Twin-2K-500 card](https://huggingface.co/datasets/LLM-Digital-Twin/Twin-2K-500)

[HCES 2022–23 access](https://microdata.gov.in/NADA/index.php/catalog/224/get-microdata) · [HCES 2023–24 access](https://microdata.gov.in/NADA/index.php/catalog/237/get-microdata) · [UCI Online Retail II](https://doi.org/10.24432/C5CG6D) · [Restricted Zenodo fig-jam experiment](https://zenodo.org/records/11655635)
