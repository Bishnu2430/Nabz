"""Survey-weighted percentiles of common lab tests from NHANES 2017–March 2020 (pre-pandemic).

Method:
- Adults aged 18 and over; pregnant participants excluded (RIDEXPRG = 1).
- Weights: the MEC exam weight (WTMECPRP) for most tests, and the fasting-subsample weight (WTSAFPRP) for
  fasting glucose, triglycerides and LDL.
- Percentiles use the weighted empirical CDF with the midpoint rule. They are point estimates;
  standard errors would need the design variables (SDMVPSU, SDMVSTRA) and aren't shown to users.
- Cells: sex (female, male and both, stored as `unknown`) × age band (18–29 … 80+). A cell needs at least
  MIN_N participants, or it's left out.
- Derived tests are computed per participant before pooling: urea = BUN × 2.14, non-HDL = TC − HDL,
  TC/HDL, VLDL = TG / 5, eAG = 28.7 × HbA1c − 46.7, eGFR by CKD-EPI 2021.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from app.analysis.percentile import AGE_BANDS, LEVELS
from app.catalogue import read_catalogue
from app.core.config import settings
from tools.synthetic.values import egfr_ckd_epi_2021

BASE_URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/"
FILES = {  # name -> sha256 of the file as downloaded on 2026-09-28
    "P_DEMO": "2e46c6c26bf77cd8989f64011ace12cbf42c0f3e03414eb59acc5328c8f87913",
    "P_CBC": "8a910eacc0fad8d3b817bb01699c5d90761c60be3b2daaaf025396b58de96ef8",
    "P_BIOPRO": "f242cb9f9da5787f77d81ffb02822350e01cea4adf072d23bc96eb008182010c",
    "P_GHB": "dac9e423f56041c2ec46486cb16be16d3347e0a81a575985882ffad5a60e1195",
    "P_TCHOL": "759cd9c408b5d1b91f6cfb5d5e67920a301f7478c0e90ce7adf4bbd277a45ac8",
    "P_HDL": "04a344f00fe34b3dc4202ee9e47cf61e67d1f985d7c9ece228e25caa85c7fbd7",
    "P_TRIGLY": "d3eb2df386f24a559ae4db992f0ec9aaf3d2c0caec173aa1921e78100ee88b31",
    "P_GLU": "91b83c46fb4707c431838159135e93693a0572bce54074f5a890f0ee104732b3",
    "P_FERTIN": "8464b13160fc38cce793f07ff1e658dae27a4c201956ef2bbde0925dd4a6f186",
}

# catalogue code -> (file, variable). Units already match the catalogue's canonical units.
MEASURED = {
    "wbc": ("P_CBC", "LBXWBCSI"), "rbc": ("P_CBC", "LBXRBCSI"), "hb": ("P_CBC", "LBXHGB"),
    "hct": ("P_CBC", "LBXHCT"), "mcv": ("P_CBC", "LBXMCVSI"), "mch": ("P_CBC", "LBXMCHSI"),
    "mchc": ("P_CBC", "LBXMC"), "rdw": ("P_CBC", "LBXRDW"), "plt": ("P_CBC", "LBXPLTSI"),
    "neut_pct": ("P_CBC", "LBXNEPCT"), "lymph_pct": ("P_CBC", "LBXLYPCT"), "mono_pct": ("P_CBC", "LBXMOPCT"),
    "eos_pct": ("P_CBC", "LBXEOPCT"), "baso_pct": ("P_CBC", "LBXBAPCT"),
    "alt": ("P_BIOPRO", "LBXSATSI"), "ast": ("P_BIOPRO", "LBXSASSI"), "alp": ("P_BIOPRO", "LBXSAPSI"),
    "ggt": ("P_BIOPRO", "LBXSGTSI"), "albumin": ("P_BIOPRO", "LBXSAL"), "globulin": ("P_BIOPRO", "LBXSGB"),
    "protein_total": ("P_BIOPRO", "LBXSTP"), "bili_total": ("P_BIOPRO", "LBXSTB"),
    "bun": ("P_BIOPRO", "LBXSBU"), "creatinine": ("P_BIOPRO", "LBXSCR"), "uric_acid": ("P_BIOPRO", "LBXSUA"),
    "sodium": ("P_BIOPRO", "LBXSNASI"), "potassium": ("P_BIOPRO", "LBXSKSI"), "chloride": ("P_BIOPRO", "LBXSCLSI"),
    "bicarbonate": ("P_BIOPRO", "LBXSC3SI"), "calcium": ("P_BIOPRO", "LBXSCA"), "phosphorus": ("P_BIOPRO", "LBXSPH"),
    "iron": ("P_BIOPRO", "LBXSIR"), "glucose_random": ("P_BIOPRO", "LBXSGL"),
    "hba1c": ("P_GHB", "LBXGH"), "chol_total": ("P_TCHOL", "LBXTC"), "hdl": ("P_HDL", "LBDHDD"),
    "ferritin": ("P_FERTIN", "LBXFER"),
    "glucose_fasting": ("P_GLU", "LBXGLU"), "tg": ("P_TRIGLY", "LBXTR"), "ldl": ("P_TRIGLY", "LBDLDL"),
}
DERIVED = ("urea", "non_hdl", "chol_hdl_ratio", "vldl", "eag", "egfr")
FASTING_CODES = {"glucose_fasting", "tg", "ldl", "vldl"}
MIN_N = 100


def data_dir() -> Path:
    return Path(settings.data_dir) / "external" / "nhanes"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, digest in FILES.items():
        path = directory / f"{name}.xpt"
        if not path.exists():
            print(f"downloading {name}.xpt")
            urllib.request.urlretrieve(BASE_URL + f"{name}.xpt", path)  # noqa: S310 - fixed https URL
        actual = sha256(path)
        if actual != digest:
            sys.exit(f"{path.name}: checksum {actual} differs from the recorded {digest}; CDC may have re-released it")
        print(f"ok  {path.name}  {path.stat().st_size:>9,} bytes")


def load(directory: Path) -> pd.DataFrame:
    """One row per adult, non-pregnant participant with every measured and derived value and both weights."""
    read = {name: pd.read_sas(directory / f"{name}.xpt", format="xport").set_index("SEQN") for name in FILES}
    demo = read["P_DEMO"]
    people = demo[(demo.RIDAGEYR >= 18) & (demo.RIDEXPRG != 1)]
    df = pd.DataFrame({
        "sex": people.RIAGENDR.map({1.0: "male", 2.0: "female"}),
        "age": people.RIDAGEYR.astype(int),
        "w_mec": people.WTMECPRP,
    })
    df["w_fast"] = read["P_GLU"].WTSAFPRP.reindex(df.index)
    for code, (name, var) in MEASURED.items():
        df[code] = read[name][var].reindex(df.index)

    df["urea"] = df.bun * 2.14
    df["non_hdl"] = df.chol_total - df.hdl
    df["chol_hdl_ratio"] = df.chol_total / df.hdl
    df["vldl"] = df.tg / 5
    df["eag"] = 28.7 * df.hba1c - 46.7
    df["egfr"] = [egfr_ckd_epi_2021(c, a, s) if pd.notna(c) and c > 0 else np.nan
                  for c, a, s in zip(df.creatinine, df.age, df.sex, strict=True)]
    return df


def weighted_percentiles(values: np.ndarray, weights: np.ndarray, levels=LEVELS) -> list[float]:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cum = (np.cumsum(w) - w / 2) / w.sum()
    return [float(np.interp(q / 100, cum, v)) for q in levels]


def build(df: pd.DataFrame, decimals: dict[str, int]) -> list[dict]:
    rows: list[dict] = []
    for code in (*MEASURED, *DERIVED):
        wcol = "w_fast" if code in FASTING_CODES else "w_mec"
        places = decimals.get(code, 1) + 1
        for sex in ("female", "male", "unknown"):
            for lo, hi in AGE_BANDS:
                cell = df[(df.age >= lo) & (df.age <= hi)]
                if sex != "unknown":
                    cell = cell[cell.sex == sex]
                cell = cell[cell[code].notna() & (cell[wcol] > 0)]
                if len(cell) < MIN_N:
                    continue
                cuts = weighted_percentiles(cell[code].to_numpy(float), cell[wcol].to_numpy(float))
                rows.append({"test_code": code, "sex": sex, "age_min": lo, "age_max": hi,
                             **{f"p{q:02d}": round(c, places) for q, c in zip(LEVELS, cuts, strict=True)},
                             "n": len(cell)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.nhanes")
    ap.add_argument("command", choices=["fetch", "build"])
    ap.add_argument("--dir", default=str(data_dir()))
    ap.add_argument("--out", default=str(Path(settings.data_dir) / "catalogue" / "population_percentiles.csv"))
    a = ap.parse_args()
    directory = Path(a.dir)
    if a.command == "fetch":
        fetch(directory)
        return
    catalogue = read_catalogue(Path(settings.data_dir) / "catalogue")
    missing = sorted({*MEASURED, *DERIVED} - {t.code for t in catalogue.tests})
    if missing:
        sys.exit(f"not in the catalogue: {missing}")
    rows = build(load(directory), {t.code: t.decimals for t in catalogue.tests})
    with Path(a.out).open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} cells for {len({r['test_code'] for r in rows})} tests to {a.out}")


if __name__ == "__main__":
    main()
