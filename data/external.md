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
