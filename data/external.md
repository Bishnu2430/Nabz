# External datasets

Public datasets Nabz derives reference data from. The raw files live in `data/external/` (git-ignored). Only the derived tables are committed.

## NHANES 2017–March 2020 (pre-pandemic)

US Centers for Disease Control and Prevention, National Center for Health Statistics. **Public domain.**
Nabz uses it for population percentiles (FR-20) and labels every comparison "US population (NHANES 2017–2020)".

Fetch and verify the files, then rebuild `data/catalogue/population_percentiles.csv`:

```bash
docker compose exec api python -m tools.nhanes fetch
```

```bash
docker compose exec api python -m tools.nhanes build
```

Source: `https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/<file>.xpt`, downloaded 2026-09-28.

| File | Contents | Bytes | SHA-256 |
|---|---|---|---|
| `P_DEMO.xpt` | Demographics, exam and interview weights | 3,614,720 | `2e46c6c26bf77cd8989f64011ace12cbf42c0f3e03414eb59acc5328c8f87913` |
| `P_CBC.xpt` | Complete blood count | 2,427,760 | `8a910eacc0fad8d3b817bb01699c5d90761c60be3b2daaaf025396b58de96ef8` |
| `P_BIOPRO.xpt` | Standard biochemistry profile | 3,420,640 | `f242cb9f9da5787f77d81ffb02822350e01cea4adf072d23bc96eb008182010c` |
| `P_GHB.xpt` | Glycohaemoglobin (HbA1c) | 167,600 | `dac9e423f56041c2ec46486cb16be16d3347e0a81a575985882ffad5a60e1195` |
| `P_TCHOL.xpt` | Total cholesterol | 294,000 | `759cd9c408b5d1b91f6cfb5d5e67920a301f7478c0e90ce7adf4bbd277a45ac8` |
| `P_HDL.xpt` | HDL cholesterol | 294,000 | `04a344f00fe34b3dc4202ee9e47cf61e67d1f985d7c9ece228e25caa85c7fbd7` |
| `P_TRIGLY.xpt` | Triglycerides and LDL (fasting subsample) | 409,360 | `d3eb2df386f24a559ae4db992f0ec9aaf3d2c0caec173aa1921e78100ee88b31` |
| `P_GLU.xpt` | Fasting plasma glucose (fasting subsample) | 164,160 | `91b83c46fb4707c431838159135e93693a0572bce54074f5a890f0ee104732b3` |
| `P_FERTIN.xpt` | Ferritin | 288,800 | `8464b13160fc38cce793f07ff1e658dae27a4c201956ef2bbde0925dd4a6f186` |

**How the percentiles are built** (`backend/tools/nhanes/__main__.py`):
- Adults aged 18 and over; pregnant participants excluded.
- Exam weights for most tests, and fasting-subsample weights for fasting glucose, triglycerides and LDL.
- Weighted 5th, 25th, 50th, 75th and 95th percentiles per sex (female, male, both) and age band (18–29 … 80+).
- A cell needs at least 100 participants.
- Urea, non-HDL, TC/HDL, VLDL, eAG and eGFR (CKD-EPI 2021) are computed per participant first.
- Result: 966 cells for 46 tests.

## MedlinePlus Connect (knowledge base)

US National Library of Medicine. NLM-authored MedlinePlus content is **in the public domain**. Pages carrying licensed third-party content (A.D.A.M.) are rejected by the build.

```bash
docker compose exec api python -m tools.knowledge fetch
```

```bash
docker compose exec api python -m tools.knowledge build
```

```bash
docker compose exec api python -m app.cli load-knowledge
```

- **fetch:** queries `https://connect.medlineplus.gov/service` once per catalogue LOINC code, at one request a second (Connect allows 100 a minute). Raw JSON responses go to `data/external/medlineplus/<loinc>.json`; 70 responses were retrieved on 2026-09-29.
- **build:** writes `data/knowledge/chunks.jsonl` (436 passages) and `data/knowledge/manifest.csv` (46 documents, each with its URL, the tests it serves, its licence and the SHA-256 of its content). Both files are committed.
- **load-knowledge:** embeds the passages and loads them into `kb_document` and `kb_chunk`.

## multilingual-e5-small (embedding model)

`intfloat/multilingual-e5-small`, **MIT licence**, as the int8 ONNX export published by Xenova on Hugging Face. It's used for retrieval only, on ONNX Runtime.

Location: `data/external/models/multilingual-e5-small/`, downloaded 2026-09-29.

| File | Source | Bytes | SHA-256 |
|---|---|---|---|
| `tokenizer.json` | `https://huggingface.co/Xenova/multilingual-e5-small/resolve/main/tokenizer.json` | 17,082,730 | `0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39` |
| `onnx/model_quantized.onnx` | `https://huggingface.co/Xenova/multilingual-e5-small/resolve/main/onnx/model_quantized.onnx` | 118,308,185 | `f80102d3f2a1229f387d3c81909990d8945513e347b0eab049f7de3c6f98c193` |
| `MODEL_CARD.md` | `https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/README.md` | 497,538 | model card, licence: MIT |

## Wikimedia Commons medical images (sample family)

Five openly licensed X-ray and MRI images (CC0, public domain, CC BY 2.0, CC BY-SA 4.0), used in the imaging reports that `python -m tools.family` gives the sample family. They are committed in [`data/imaging/`](imaging/README.md), which lists each file's author, licence, size and SHA-256. Downloaded 2026-09-30.
